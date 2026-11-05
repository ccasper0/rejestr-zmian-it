"""Database access: async engine, per-request session, health probe.

The running API connects as role ``app_rw`` (``DATABASE_URL``). Migrations use
``app_owner`` (``MIGRATIONS_DATABASE_URL``) — see ``alembic/env.py``.

All endpoints MUST obtain the database session through :data:`SessionDep` (never
``Depends(get_session)``), so the transaction is committed before the response is sent.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings

logger = logging.getLogger(__name__)

SEPARATE_TRANSACTION_INFO_KEY = "separate_transaction"
"""``session.info`` marker of sessions opened by :func:`run_in_separate_transaction`."""

SEPARATE_TRANSACTION_LOCK_TIMEOUT_MS = 5000


class Database:
    """Owns the engines and session factories for one application instance.

    Two connection pools (ADR 0010 §5):

    - the MAIN pool (``engine`` / ``sessionmaker``): request transactions (``SessionDep``),
      CLI and worker;
    - the AUXILIARY pool (``aux_engine`` / ``aux_sessionmaker``): only the short separate
      transactions of :func:`run_in_separate_transaction` (identity resolution / JIT /
      profile sync, ``login``, ``login_failed``, ``access_denied``). Such a transaction is
      often opened while the request transaction already holds a main-pool connection
      (e.g. recording a denial after the memberships were read). Taken from the same pool,
      N concurrent requests holding all N connections would each wait for a second one
      that nobody returns — a pool self-deadlock that stalls the whole process until the
      pool timeout. An auxiliary transaction never needs a main-pool connection, so the
      wait graph has no cycle: at worst it queues behind other short auxiliary
      transactions.
    """

    def __init__(
        self,
        url: str,
        *,
        health_timeout_seconds: float = 2.0,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        aux_pool_size: int = 2,
        aux_max_overflow: int = 3,
    ) -> None:
        # Creating the engines does not connect; connections are opened lazily.
        self.engine: AsyncEngine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
        )
        self.sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False
        )
        self.aux_engine: AsyncEngine = create_async_engine(
            url,
            pool_pre_ping=True,
            pool_size=aux_pool_size,
            max_overflow=aux_max_overflow,
            pool_timeout=pool_timeout,
        )
        self.aux_sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.aux_engine, expire_on_commit=False
        )
        self.health_timeout_seconds = health_timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> Database:
        return cls(
            settings.database_url,
            health_timeout_seconds=settings.db_health_timeout_seconds,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            aux_pool_size=settings.db_aux_pool_size,
            aux_max_overflow=settings.db_aux_max_overflow,
        )

    async def ping(self) -> bool:
        """Run ``SELECT 1``; return False on any failure or timeout (never raises)."""
        try:
            async with asyncio.timeout(self.health_timeout_seconds):
                async with self.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("Database health check failed: %s", type(exc).__name__)
            return False
        return True

    async def dispose(self) -> None:
        await self.engine.dispose()
        await self.aux_engine.dispose()


async def set_current_user(session: AsyncSession, user_id: UUID) -> None:
    """Record the authenticated user in the transaction (``app.user_id``).

    Set before the user's memberships are read, so the Row-Level Security policy of
    ``company_memberships`` (``user_id = app_user_id()``, migration 0003, ADR 0008) lets a
    user see their own membership rows before the company scope exists.
    """
    if not session.in_transaction():
        raise RuntimeError("set_current_user() must run inside a transaction")
    await session.execute(
        text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(UUID(str(user_id)))}
    )


async def apply_company_scope(
    session: AsyncSession,
    company_ids: Sequence[UUID],
    *,
    global_audit_read: bool = False,
    admin_scope: bool = False,
) -> None:
    """Restrict the current transaction to the given companies (Row-Level Security).

    Transaction-local equivalent of ``SET LOCAL app.company_ids = '{...}'`` (``SET LOCAL``
    does not accept bind parameters, so ``set_config(..., true)`` with binds is used — never
    string formatting). RLS policies read it through the SQL function ``app_company_ids()``
    (migration 0001), which treats a missing/empty setting as "no company";
    ``app.admin_scope`` through ``app_admin_scope()`` (migration 0003, ADR 0008).

    ``global_audit_read`` opens the separate, explicit path for reading the global audit
    chain (``company_id IS NULL``) — only for app admins (ADR 0006 §6): the global chain
    holds data of every company (names, NIP, user e-mails).

    ``admin_scope`` (``app.admin_scope = 'on'``) marks the explicit administrative path of
    an app admin (companies, dictionaries, role assignment — CLAUDE.md §7 pt 2, ADR 0007).
    It is set only by the admin-path permission dependencies in ``app.permissions``.

    Must run inside the transaction it scopes (it is reset at COMMIT/ROLLBACK). Called on
    every authenticated request by ``app.auth.dependencies.get_current_user``.
    """
    if not session.in_transaction():
        raise RuntimeError("apply_company_scope() must run inside a transaction")
    ids = "{" + ",".join(sorted({str(UUID(str(i))) for i in company_ids})) + "}"
    await session.execute(
        text(
            "SELECT set_config('app.company_ids', :ids, true), "
            "set_config('app.audit_global_read', :global_read, true), "
            "set_config('app.admin_scope', :admin_scope, true)"
        ),
        {
            "ids": ids,
            "global_read": "on" if global_audit_read else "off",
            "admin_scope": "on" if admin_scope else "off",
        },
    )


async def run_in_separate_transaction[T](
    db: Database,
    fn: Callable[[AsyncSession], Awaitable[T]],
    *,
    outer: AsyncSession | None = None,
    lock_timeout_ms: int = SEPARATE_TRANSACTION_LOCK_TIMEOUT_MS,
    company_ids: Sequence[UUID] = (),
    user_id: UUID | None = None,
    main_pool: bool = False,
) -> T:
    """Run ``fn`` in its own short transaction, COMMITTED before this function returns.

    For writes that must not share the fate (or the locks) of the request's business
    transaction (ADR 0007 §2):

    - JIT provisioning and profile sync of the authenticated user — they write to the
      GLOBAL audit chain; inside the request transaction they would hold the global head
      until COMMIT, before the endpoint locks company rows / company chains, which
      reverses the lock order of ADR 0006 §7 and deadlocks (stage 1 review);
    - (stage 2) ``login`` / ``login_failed`` / ``access_denied`` audit events, which must
      survive the rollback of the failing request.

    The session starts with an EMPTY company scope (RLS: only global audit entries can be
    written, no company rows are visible) and ``lock_timeout`` set, so a programming error
    that makes it wait for a lock held by the caller fails instead of hanging.
    ``company_ids`` / ``user_id``: a narrower explicit scope for writes that belong to
    company chains (e.g. the ``integrity_failed`` entry of a report download, ADR 0017
    §14) - never ``admin_scope``, never the global audit read.

    ``outer``: the caller's request session, if any. Refused when that transaction already
    holds an audit chain head lock (``app.services.audit.held_chain_locks``): the inner
    transaction may need the same head and would wait for the outer one, which in turn
    waits for us — a deadlock PostgreSQL cannot detect (one side is the application).
    Call this BEFORE the request transaction takes any lock. The connection comes from
    the AUXILIARY pool (:class:`Database`), never from the pool ``outer`` holds a
    connection of, so a full main pool cannot deadlock it.

    ``main_pool``: take the connection from the MAIN pool. Only for callers that hold no
    connection at all (``outer`` must be ``None``): the public login / refresh endpoints
    of local accounts (ADR 0018 §6), so that a flood of login attempts cannot exhaust the
    small auxiliary pool every authenticated request needs.

    On exception the transaction is rolled back and the exception propagates.
    """
    if main_pool and outer is not None:
        raise RuntimeError("main_pool=True is only allowed without an outer transaction")
    if outer is not None:
        from app.services.audit import held_chain_locks

        held = held_chain_locks(outer)
        if held:
            chains = ", ".join(sorted("global" if c is None else str(c) for c in held))
            raise RuntimeError(
                "run_in_separate_transaction() called while the outer transaction holds "
                f"audit chain lock(s): {chains}"
            )
    maker = db.sessionmaker if main_pool else db.aux_sessionmaker
    async with maker() as session:
        session.info[SEPARATE_TRANSACTION_INFO_KEY] = True
        async with session.begin():
            await session.execute(
                text("SELECT set_config('lock_timeout', :timeout, true)"),
                {"timeout": f"{int(lock_timeout_ms)}ms"},
            )
            if user_id is not None:
                await set_current_user(session, user_id)
            await apply_company_scope(session, company_ids)
            result = await fn(session)
    return result


async def run_read_only[T](
    db: Database,
    fn: Callable[[AsyncSession], Awaitable[T]],
    *,
    company_ids: Sequence[UUID],
) -> T:
    """Run ``fn`` in its own short READ ONLY transaction scoped to ``company_ids``.

    For reads that need a wider company scope than the request transaction may have
    (ADR 0015 §2: counters of the admin's company list). The request transaction is never
    widened: this one is separate (auxiliary pool, like :func:`run_in_separate_transaction`),
    starts with ``SET TRANSACTION READ ONLY`` (PostgreSQL rejects every write), has no
    ``admin_scope`` and no global audit read, and is rolled back at the end.
    """
    async with db.aux_sessionmaker() as session:
        try:
            # The first statement of the (auto-begun) transaction.
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await apply_company_scope(session, company_ids)
            return await fn(session)
        finally:
            await session.rollback()


@asynccontextmanager
async def snapshot_session(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    company_ids: Sequence[UUID],
    user_id: UUID,
) -> AsyncIterator[AsyncSession]:
    """A REPEATABLE READ, READ ONLY transaction scoped to ``company_ids`` as ``user_id``.

    Every query sees ONE snapshot (taken at the first query), so data read by several
    queries is mutually consistent - the report data of a background generation (ADR 0017
    §14). The isolation level is set by the first statement of the transaction, before
    anything is read; the transaction is always rolled back (it cannot write anyway).
    """
    async with sessionmaker() as session:
        try:
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            await set_current_user(session, user_id)
            await apply_company_scope(session, company_ids)
            yield session
        finally:
            await session.rollback()


async def set_transaction_read_only(session: AsyncSession) -> None:
    """Make the CURRENT transaction read-only (``transaction_read_only = on``).

    PostgreSQL allows switching a transaction to read-only after it has run queries (the
    reverse is refused), so a narrow read path can be locked down once it has been chosen
    (ADR 0015 §7: the admin reading a company audit chain without membership).
    """
    await session.execute(text("SET TRANSACTION READ ONLY"))


def get_database(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session and one transaction per request; committed on success.

    Do not depend on this function directly — use :data:`SessionDep`. The commit happens
    when the dependency exits; only with ``scope="function"`` does that happen BEFORE the
    response is sent (see ``SessionDep``).

    The company scope (RLS) is applied in the same transaction by ``get_current_user``
    (``app.auth.dependencies``) right after the user is loaded; FastAPI caches this
    dependency per request, so the endpoint receives that very session.
    """
    db = get_database(request)
    async with db.sessionmaker() as session, session.begin():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
"""The ONLY way endpoints may obtain a database session: ``session: SessionDep``.

``scope="function"`` makes FastAPI close the dependency (i.e. COMMIT, or ROLLBACK on
exception) right after the endpoint returns and BEFORE the response is sent. With the
default request scope the commit would run after a 2xx was already sent, so a failing
commit (deferred constraint, serialization error, lost connection) would leave the client
believing that data — and its audit entry — were saved. A commit failure now surfaces as
500 problem+json (tested in ``tests/test_db_session.py``).
"""


async def check_database(request: Request) -> bool:
    """FastAPI dependency used by the health endpoint (overridable in tests)."""
    return await get_database(request).ping()
