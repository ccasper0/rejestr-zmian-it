"""``run_in_separate_transaction`` - the short own transaction of identity resolution and
authentication events (ADR 0007 §2, ADR 0010 §5): committed independently of the request,
rolled back on error, refused while the outer transaction holds a chain lock, with a lock
timeout. (The OIDC profile-sync tests were removed with OIDC, ADR 0018.)
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Database, run_in_separate_transaction
from app.domain.audit import Actor, AuditAction, EntityType
from app.models import User
from app.services import audit
from app.services import users as users_service
from tests.conftest import DbUrls

pytestmark = pytest.mark.db


# --------------------------------------------------------------------------- helper


async def test_separate_transaction_commits_independently(db_urls: DbUrls) -> None:
    db = Database(db_urls.rw)
    suffix = uuid4().hex[:10]
    try:
        async with db.sessionmaker() as outer, outer.begin():

            async def create(session: AsyncSession) -> User:
                return await users_service.create_user(
                    session,
                    actor=Actor.system(),
                    external_id=f"sep-{suffix}",
                    email=f"sep-{suffix}@example.com",
                    display_name="Osobna Transakcja",
                )

            created = await run_in_separate_transaction(db, create, outer=outer)
            await outer.rollback()
        async with db.sessionmaker() as check, check.begin():
            found = await users_service.get_user_by_external_id(check, f"sep-{suffix}")
        assert found is not None
        assert found.id == created.id
    finally:
        await db.dispose()


async def test_separate_transaction_rolls_back_on_error(db_urls: DbUrls) -> None:
    db = Database(db_urls.rw)
    suffix = uuid4().hex[:10]

    async def create_then_fail(session: AsyncSession) -> None:
        await users_service.create_user(
            session,
            actor=Actor.system(),
            external_id=f"sep-fail-{suffix}",
            email=f"sep-fail-{suffix}@example.com",
            display_name="Wycofana",
        )
        raise RuntimeError("boom")

    try:
        with pytest.raises(RuntimeError, match="boom"):
            await run_in_separate_transaction(db, create_then_fail)
        async with db.sessionmaker() as check, check.begin():
            assert await users_service.get_user_by_external_id(check, f"sep-fail-{suffix}") is None
    finally:
        await db.dispose()


async def test_separate_transaction_refuses_while_outer_holds_a_chain_lock(
    db_urls: DbUrls,
) -> None:
    """Holding a chain head in the outer transaction would make the inner one wait forever."""
    db = Database(db_urls.rw)

    async def noop(session: AsyncSession) -> None:
        return None

    try:
        async with db.sessionmaker() as outer, outer.begin():
            await audit.record(
                outer,
                company_id=None,
                actor=Actor.system(),
                entity_type=EntityType.AUDIT,
                entity_id=None,
                action=AuditAction.VERIFY,
            )
            assert audit.held_chain_locks(outer) == frozenset({None})
            with pytest.raises(RuntimeError, match="audit chain"):
                await run_in_separate_transaction(db, noop, outer=outer)
            await outer.rollback()
        # A new transaction of the same session starts without recorded locks.
        async with db.sessionmaker() as outer, outer.begin():
            assert audit.held_chain_locks(outer) == frozenset()
            await run_in_separate_transaction(db, noop, outer=outer)
    finally:
        await db.dispose()


async def test_separate_transaction_has_a_lock_timeout(db_urls: DbUrls) -> None:
    db = Database(db_urls.rw)

    async def read_timeout(session: AsyncSession) -> str:
        from sqlalchemy import text

        value: str = (await session.execute(text("SHOW lock_timeout"))).scalar_one()
        return value

    try:
        assert await run_in_separate_transaction(db, read_timeout) == "5s"
    finally:
        await db.dispose()
