"""Row-Level Security at the database level (CLAUDE.md §7 pt 2, ADR 0006, ADR 0008).

Everything here runs as ``app_rw`` (not the owner, ``NOBYPASSRLS``) WITHOUT the
application's own filters, so it proves that the database alone isolates companies.

The guard tests (introspection of ``pg_class`` / ``pg_policies``) make it impossible to
add a table with ``company_id`` (changes, CI, attachments, ...) without RLS: a new table
fails here until it has policies, or is listed in ``RLS_EXEMPT`` with a justification
(which requires an ADR).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.auth.dependencies import CurrentUserDep
from app.db import SessionDep, apply_company_scope, set_current_user
from app.errors import ProblemError
from app.main import create_app
from app.permissions import Role
from app.services import audit as audit_service
from app.services import companies as companies_service
from app.services import memberships as memberships_service
from tests.conftest import DbUrls, make_settings
from tests.factories import SYSTEM, World, auth, client_for

pytestmark = pytest.mark.db

INSUFFICIENT_PRIVILEGE = "42501"

# Tenant key of tables that ARE the tenant (no company_id column).
TENANT_ROOTS: dict[str, str] = {"companies": "id"}
# table -> justification. Must stay empty unless an ADR says otherwise.
RLS_EXEMPT: dict[str, str] = {}
# A policy expression must depend on at least one of the transaction-scope functions.
SCOPE_FUNCTIONS = ("app_company_ids()", "app_admin_scope()", "app_user_id()")
PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE")


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@asynccontextmanager
async def tx(
    engine: AsyncEngine,
    company_ids: Sequence[UUID] = (),
    *,
    admin: bool = False,
    user_id: UUID | None = None,
    global_read: bool = False,
) -> AsyncIterator[AsyncSession]:
    """One transaction scoped like a request; rolled back at the end (no side effects)."""
    async with AsyncSession(engine) as session:
        await session.begin()
        if user_id is not None:
            await set_current_user(session, user_id)
        await apply_company_scope(
            session, company_ids, global_audit_read=global_read, admin_scope=admin
        )
        try:
            yield session
        finally:
            await session.rollback()


async def scalar(session: AsyncSession, sql: str, **params: Any) -> Any:
    return (await session.execute(text(sql), params)).scalar_one()


async def ids(session: AsyncSession, sql: str, **params: Any) -> set[UUID]:
    return set((await session.execute(text(sql), params)).scalars().all())


async def expect_denied(
    engine: AsyncEngine, sql: str, company_ids: Sequence[UUID] = (), **kwargs: Any
) -> None:
    """The statement violates an RLS policy (WITH CHECK): 42501, nothing written."""
    params = kwargs.pop("params", {})
    with pytest.raises(DBAPIError) as info:
        async with tx(engine, company_ids, **kwargs) as session:
            await session.execute(text(sql), params)
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE, info.value
    assert "row-level security" in str(info.value)


async def rowcount(
    engine: AsyncEngine, sql: str, company_ids: Sequence[UUID] = (), **kwargs: Any
) -> int:
    params = kwargs.pop("params", {})
    async with tx(engine, company_ids, **kwargs) as session:
        result = await session.execute(text(sql), params)
        return int(result.rowcount)  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- guards


async def tenant_tables(conn: Any) -> dict[str, dict[str, Any]]:
    """Every table in ``public`` with a ``company_id`` column, plus the tenant roots."""
    rows = (
        await conn.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                       pg_get_userbyid(c.relowner) AS owner
                  FROM pg_class c
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
                   AND (c.relname = ANY (:roots) OR EXISTS (
                        SELECT 1 FROM pg_attribute a
                         WHERE a.attrelid = c.oid AND a.attname = 'company_id'
                           AND NOT a.attisdropped))
                """
            ),
            {"roots": list(TENANT_ROOTS)},
        )
    ).all()
    return {r.relname: dict(r._mapping) for r in rows}


async def rls_problems(conn: Any) -> tuple[set[str], list[str]]:
    """(tenant tables found, problems) - the guard itself, reused by its mutation test."""
    tables = await tenant_tables(conn)
    policies = (
        await conn.execute(
            text(
                "SELECT tablename, policyname, permissive, roles, cmd, qual, with_check "
                "FROM pg_policies WHERE schemaname = 'public'"
            )
        )
    ).all()
    granted = {
        (table, privilege)
        for table in tables
        for privilege in PRIVILEGES
        if (
            await conn.execute(
                text("SELECT has_table_privilege('app_rw', :t, :p)"),
                {"t": f"public.{table}", "p": privilege},
            )
        ).scalar_one()
    }
    problems: list[str] = []
    for name, table in sorted(tables.items()):
        if name in RLS_EXEMPT:
            continue
        if not table["relrowsecurity"]:
            problems.append(f"{name}: ROW LEVEL SECURITY is not enabled")
        if table["owner"] != "app_owner":
            problems.append(f"{name}: owned by {table['owner']} (owner bypasses RLS)")
        own = [p for p in policies if p.tablename == name]
        if not own:
            problems.append(f"{name}: no policy")
        for policy in own:
            if not ({"app_rw", "public"} & set(policy.roles)):
                problems.append(f"{name}.{policy.policyname}: does not apply to app_rw")
            for expression in (policy.qual, policy.with_check):
                if expression is not None and not any(f in expression for f in SCOPE_FUNCTIONS):
                    problems.append(
                        f"{name}.{policy.policyname}: expression ignores the transaction "
                        f"scope: {expression}"
                    )
        # Every command app_rw may run is covered by an explicit permissive policy
        # (otherwise RLS silently denies it - safe, but a sign of a forgotten policy).
        for privilege in PRIVILEGES:
            if (name, privilege) in granted and not any(
                p.permissive == "PERMISSIVE" and p.cmd in (privilege, "ALL") for p in own
            ):
                problems.append(f"{name}: app_rw has {privilege} but no {privilege} policy")
    return set(tables), problems


async def test_every_table_with_company_id_has_rls_and_policies(rw_engine: AsyncEngine) -> None:
    async with rw_engine.connect() as conn:
        tables, problems = await rls_problems(conn)
    # The query must find the known tenant tables (otherwise the guard is vacuous).
    assert {
        "companies",
        "company_memberships",
        "audit_log",
        "audit_chain_heads",
        "company_categories",
        "configuration_items",
        "changes",
        "change_items",
        "change_ci_consents",
        "change_comments",
        "attachments",
        "number_sequences",
    } <= tables
    assert problems == []
    assert set(RLS_EXEMPT) <= tables  # no stale exemptions


async def test_guard_detects_a_forgotten_policy(owner_engine: AsyncEngine) -> None:
    """Mutation test of the guard: new tenant tables without RLS, without policies, or with
    a policy ignoring the scope are reported. DDL is transactional - rolled back."""
    async with owner_engine.connect() as conn:
        await conn.execute(text("CREATE TABLE rls_probe_plain (company_id uuid)"))
        await conn.execute(text("CREATE TABLE rls_probe_nopolicy (company_id uuid)"))
        await conn.execute(text("ALTER TABLE rls_probe_nopolicy ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text("CREATE TABLE rls_probe_open (company_id uuid)"))
        await conn.execute(text("ALTER TABLE rls_probe_open ENABLE ROW LEVEL SECURITY"))
        await conn.execute(
            text("CREATE POLICY rls_probe_open_all ON rls_probe_open TO app_rw USING (true)")
        )
        tables, problems = await rls_problems(conn)
        await conn.rollback()
    assert {"rls_probe_plain", "rls_probe_nopolicy", "rls_probe_open"} <= tables
    assert "rls_probe_plain: ROW LEVEL SECURITY is not enabled" in problems
    assert "rls_probe_plain: no policy" in problems
    assert "rls_probe_nopolicy: no policy" in problems
    assert any(p.startswith("rls_probe_nopolicy: app_rw has SELECT") for p in problems)
    assert any(p.startswith("rls_probe_open.rls_probe_open_all: expression") for p in problems)
    assert not any(p.startswith(("companies", "company_memberships", "audit_")) for p in problems)


async def test_no_forced_rls_and_app_rw_owns_nothing(rw_engine: AsyncEngine) -> None:
    """ADR 0008 §2: app_rw is never an owner (an owner bypasses non-forced RLS) and cannot
    create objects; FORCE is deliberately not used."""
    async with rw_engine.connect() as conn:
        tables = await tenant_tables(conn)
        owned = (
            await conn.execute(
                text(
                    "SELECT c.relname FROM pg_class c JOIN pg_namespace n "
                    "ON n.oid = c.relnamespace WHERE n.nspname = 'public' "
                    "AND pg_get_userbyid(c.relowner) = 'app_rw'"
                )
            )
        ).all()
        can_create = (
            await conn.execute(text("SELECT has_schema_privilege('app_rw', 'public', 'CREATE')"))
        ).scalar_one()
    assert owned == []
    assert can_create is False
    assert not any(t["relforcerowsecurity"] for t in tables.values())


async def test_no_rls_bypass_through_views_or_definer_functions(rw_engine: AsyncEngine) -> None:
    """Views run with the owner's rights unless ``security_invoker``; SECURITY DEFINER
    functions run as the owner. Either would bypass RLS if app_rw could use it."""
    async with rw_engine.connect() as conn:
        views = (
            await conn.execute(
                text(
                    "SELECT c.relname FROM pg_class c JOIN pg_namespace n "
                    "ON n.oid = c.relnamespace WHERE n.nspname = 'public' "
                    "AND c.relkind IN ('v', 'm') "
                    "AND has_table_privilege('app_rw', c.oid, 'SELECT') "
                    "AND NOT coalesce('security_invoker=true' = ANY (c.reloptions), false)"
                )
            )
        ).all()
        definers = (
            await conn.execute(
                text(
                    "SELECT p.proname FROM pg_proc p JOIN pg_namespace n "
                    "ON n.oid = p.pronamespace WHERE n.nspname = 'public' AND p.prosecdef "
                    "AND has_function_privilege('app_rw', p.oid, 'EXECUTE')"
                )
            )
        ).all()
    assert views == []
    assert definers == []


async def test_tenant_rows_invisible_without_scope_in_every_tenant_table(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Behavioural guard over all tenant tables: a transaction scoped to an unrelated
    company (no admin path, no user, no global audit read) sees no tenant row."""
    async with rw_engine.connect() as conn:
        tables = await tenant_tables(conn)
    async with tx(rw_engine, [uuid4()]) as session:
        visible = {
            name: await scalar(
                session,
                f"SELECT count(*) FROM {name} "  # noqa: S608 - names from pg_class
                f"WHERE {TENANT_ROOTS.get(name, 'company_id')} IS NOT NULL",
            )
            for name in tables
            if name not in RLS_EXEMPT
        }
    assert visible == dict.fromkeys(visible, 0)


# --------------------------------------------------------------------------- helpers in SQL


async def test_scope_functions_are_safe_by_default(rw_engine: AsyncEngine) -> None:
    sql = "SELECT app_user_id(), app_admin_scope(), app_company_ids(), app_global_audit_read()"
    async with rw_engine.connect() as conn:
        assert tuple((await conn.execute(text(sql))).one()) == (None, False, [], False)
        # Set and reverted (transaction-local): '' afterwards on a pooled connection.
        await conn.execute(
            text(
                "SELECT set_config('app.user_id', :u, true), "
                "set_config('app.admin_scope', 'on', true)"
            ),
            {"u": str(uuid4())},
        )
        await conn.commit()
        assert tuple((await conn.execute(text(sql))).one()) == (None, False, [], False)
        for value in ("off", "ON", "true", "1", ""):
            await conn.execute(text("SELECT set_config('app.admin_scope', :v, true)"), {"v": value})
            assert (await conn.execute(text("SELECT app_admin_scope()"))).scalar_one() is False
        await conn.rollback()


# --------------------------------------------------------------------------- reading


async def test_company_scope_shows_only_own_company(rw_engine: AsyncEngine, world: World) -> None:
    a, b = world.a.id, world.b.id
    async with tx(rw_engine, [a]) as session:
        companies = await ids(session, "SELECT id FROM companies")
        members = await ids(session, "SELECT DISTINCT company_id FROM company_memberships")
        member_count = await scalar(session, "SELECT count(*) FROM company_memberships")
        audit = await ids(
            session,
            "SELECT DISTINCT company_id FROM audit_log WHERE company_id = ANY (:c)",
            c=[a, b],
        )
        heads = await ids(
            session, "SELECT company_id FROM audit_chain_heads WHERE company_id IS NOT NULL"
        )
        # Even an explicit lookup of B's id finds nothing.
        direct_b = await scalar(session, "SELECT count(*) FROM companies WHERE id = :b", b=b)
    assert companies == {a}
    assert members == {a}
    assert member_count == 4  # approver, editor, auditor, viewer of A
    assert audit == {a}  # role grants of A are in A's chain
    assert heads == {a}
    assert direct_b == 0


async def test_no_scope_means_no_rows_not_an_error(rw_engine: AsyncEngine, world: World) -> None:
    queries = {
        "companies": "SELECT count(*) FROM companies",
        "company_memberships": "SELECT count(*) FROM company_memberships",
        "audit_log": "SELECT count(*) FROM audit_log",
        # The global head is shared by design (ADR 0006 §6): only company heads count.
        "audit_chain_heads": (
            "SELECT count(*) FROM audit_chain_heads WHERE company_id IS NOT NULL"
        ),
    }
    async with rw_engine.connect() as conn:
        unscoped = {k: (await conn.execute(text(q))).scalar_one() for k, q in queries.items()}
        # A pooled connection reused after a scoped transaction must not keep the scope.
        await conn.execute(
            text(
                "SELECT set_config('app.company_ids', :c, true), "
                "set_config('app.admin_scope', 'on', true), "
                "set_config('app.audit_global_read', 'on', true)"
            ),
            {"c": "{" + f"{world.a.id},{world.b.id}" + "}"},
        )
        scoped = {k: (await conn.execute(text(q))).scalar_one() for k, q in queries.items()}
        await conn.commit()
        after = {k: (await conn.execute(text(q))).scalar_one() for k, q in queries.items()}
    assert unscoped == dict.fromkeys(queries, 0)
    assert all(v > 0 for v in scoped.values()), scoped
    assert after == dict.fromkeys(queries, 0)


async def test_user_id_reveals_only_own_memberships(rw_engine: AsyncEngine, world: World) -> None:
    """``app.user_id`` alone (before the company scope exists) shows the caller's own
    membership rows - and nothing else."""
    async with tx(rw_engine, user_id=world.outsider.id) as session:
        rows = (
            await session.execute(text("SELECT user_id, company_id FROM company_memberships"))
        ).all()
        companies = await scalar(session, "SELECT count(*) FROM companies")
        roles = await memberships_service.roles_by_company(session, world.outsider.id)
        others = await memberships_service.roles_by_company(session, world.editor.id)
    assert {(r.user_id, r.company_id) for r in rows} == {(world.outsider.id, world.b.id)}
    assert len(rows) == 2  # editor + approver in B
    assert companies == 0
    assert set(roles) == {world.b.id}
    assert others == {}


async def test_admin_scope_reads_identity_but_not_audit(
    rw_engine: AsyncEngine, world: World
) -> None:
    """The admin path opens companies and memberships, never the audit log: company chains
    need the company in scope, the global chain needs ``audit_global_read``."""
    a, b = world.a.id, world.b.id
    async with tx(rw_engine, admin=True) as session:
        companies = await ids(session, "SELECT id FROM companies WHERE id = ANY (:c)", c=[a, b])
        members = await ids(session, "SELECT DISTINCT company_id FROM company_memberships")
        audit = await scalar(session, "SELECT count(*) FROM audit_log")
        heads = await scalar(
            session, "SELECT count(*) FROM audit_chain_heads WHERE company_id = ANY (:c)", c=[a, b]
        )
    assert companies == {a, b}
    assert {a, b} <= members
    assert (audit, heads) == (0, 0)

    async with tx(rw_engine, [a], admin=True) as session:
        chains = await ids(session, "SELECT DISTINCT company_id FROM audit_log")
    assert chains == {a}

    async with tx(rw_engine, admin=True, global_read=True) as session:
        chains_global = await ids(session, "SELECT DISTINCT company_id FROM audit_log")
    assert chains_global == {None}


async def test_services_cannot_leak_even_without_application_filters(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Defence in depth: service calls that would leak data if the application layer had
    a bug (no company filter / a foreign id) return nothing under RLS."""
    async with tx(rw_engine, [world.a.id]) as session:
        everything, total = await companies_service.list_companies(
            session, company_ids=None, limit=100, offset=0
        )
        foreign = await companies_service.get_company(session, world.b.id)
        by_prefix = await companies_service.get_company_by_prefix(session, world.b.prefix)
        foreign_members = await memberships_service.list_members(session, world.b.id)
        outsider_roles = await memberships_service.roles_by_company(session, world.outsider.id)
        listed = [c.id for c in everything]
    assert (listed, total) == ([world.a.id], 1)
    assert (foreign, by_prefix) == (None, None)
    assert foreign_members == []
    assert outsider_roles == {}


async def audit_counts(engine: AsyncEngine, world: World) -> tuple[int, int]:
    """(entries in the chains of A and B, entries in the global chain)."""
    async with tx(engine, [world.a.id, world.b.id], global_read=True) as session:
        company = await scalar(
            session, "SELECT count(*) FROM audit_log WHERE company_id IS NOT NULL"
        )
        global_ = await scalar(session, "SELECT count(*) FROM audit_log WHERE company_id IS NULL")
    return int(company), int(global_)


async def test_services_cannot_modify_outside_the_admin_scope(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Defence in depth for writes: even if a service were called on a wrong path, the
    company row it locks is invisible - 404, and nothing (not even audit) is written."""
    before = await audit_counts(rw_engine, world)
    attempts = [
        ([world.a.id], False, world.a.id),  # member scope, no admin path
        ([world.a.id], True, world.b.id),  # admin path, but another company
    ]
    for scope, admin, target in attempts:
        async with tx(rw_engine, scope, admin=admin) as session:
            for operation in (
                companies_service.update_company(
                    session, actor=SYSTEM, company_id=target, changes={"is_ksc_entity": True}
                ),
                companies_service.archive_company(session, actor=SYSTEM, company_id=target),
                memberships_service.set_member_roles(
                    session,
                    actor=SYSTEM,
                    company_id=target,
                    user_id=world.nobody.id,
                    roles={Role.VIEWER},
                ),
            ):
                with pytest.raises(ProblemError) as info:
                    await operation
                assert (info.value.status, info.value.code) == (404, "company.not_found")
    assert await audit_counts(rw_engine, world) == before
    async with tx(rw_engine, [world.a.id, world.b.id], admin=True) as session:
        statuses = await ids(
            session, "SELECT status FROM companies WHERE id = ANY (:c)", c=[world.a.id, world.b.id]
        )
        nobody = await memberships_service.roles_by_company(session, world.nobody.id)
    assert statuses == {"active"}
    assert nobody == {}


# --------------------------------------------------------------------------- writing


async def test_member_scope_cannot_write_identity_tables(
    rw_engine: AsyncEngine, world: World
) -> None:
    a, b = world.a.id, world.b.id
    insert_member = (
        "INSERT INTO company_memberships (user_id, company_id, role) VALUES (:u, :c, 'viewer')"
    )
    await expect_denied(
        rw_engine,
        "INSERT INTO companies (name, prefix) VALUES ('Nowa', 'NOWAQX')",
        [a],
    )
    for company in (a, b):
        await expect_denied(
            rw_engine, insert_member, [a], params={"u": world.nobody.id, "c": company}
        )
    # Updates and deletes simply do not see the rows (0 rows, no error).
    for company in (a, b):
        assert (
            await rowcount(
                rw_engine,
                "UPDATE companies SET is_ksc_entity = true WHERE id = :c",
                [a],
                params={"c": company},
            )
            == 0
        )
        for sql in (
            "UPDATE company_memberships SET role = 'viewer' WHERE company_id = :c",
            "DELETE FROM company_memberships WHERE company_id = :c",
        ):
            assert await rowcount(rw_engine, sql, [a], params={"c": company}) == 0


async def test_admin_scope_writes_only_within_the_scope(
    rw_engine: AsyncEngine, world: World
) -> None:
    a, b = world.a.id, world.b.id
    await expect_denied(
        rw_engine,
        "INSERT INTO company_memberships (user_id, company_id, role) VALUES (:u, :c, 'viewer')",
        [a],
        admin=True,
        params={"u": world.nobody.id, "c": b},
    )
    # Moving a membership row into a company outside the scope violates WITH CHECK.
    await expect_denied(
        rw_engine,
        "UPDATE company_memberships SET company_id = :b WHERE company_id = :a",
        [a],
        admin=True,
        params={"a": a, "b": b},
    )
    for sql in (
        "UPDATE companies SET is_ksc_entity = true WHERE id = :c",
        "UPDATE company_memberships SET role = role WHERE company_id = :c",
        "DELETE FROM company_memberships WHERE company_id = :c",
    ):
        assert await rowcount(rw_engine, sql, [a], admin=True, params={"c": b}) == 0
        assert await rowcount(rw_engine, sql, [a], admin=True, params={"c": a}) > 0
    # A new company: the admin path alone is enough (it cannot be in the scope yet).
    assert (
        await rowcount(
            rw_engine,
            "INSERT INTO companies (name, prefix) VALUES ('Nowa RLS', 'NOWARLS')",
            admin=True,
        )
        == 1
    )


async def test_company_rows_can_only_be_locked_on_the_admin_path(
    rw_engine: AsyncEngine, world: World
) -> None:
    """``SELECT ... FOR UPDATE`` is subject to the UPDATE policy as well (ADR 0008)."""
    sql = "SELECT id FROM companies WHERE id = :a FOR UPDATE"
    async with tx(rw_engine, [world.a.id]) as session:
        member = await ids(session, sql, a=world.a.id)
    async with tx(rw_engine, [world.a.id], admin=True) as session:
        admin = await ids(session, sql, a=world.a.id)
    assert (member, admin) == (set(), {world.a.id})


async def test_archive_and_prefix_rules_hold_under_rls(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Stage 1 criteria at the database level: companies are archived, never deleted
    (not even on the admin path); only the admin path archives; members still see an
    archived company; the prefix cannot change."""
    b = world.b.id
    with pytest.raises(DBAPIError) as info:
        async with tx(rw_engine, [b], admin=True) as session:
            await session.execute(text("DELETE FROM companies WHERE id = :b"), {"b": b})
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE

    archive = "UPDATE companies SET status = 'archived' WHERE id = :b"
    assert await rowcount(rw_engine, archive, [b], params={"b": b}) == 0
    async with AsyncSession(rw_engine) as session, session.begin():
        await apply_company_scope(session, [b], admin_scope=True)
        assert (await session.execute(text(archive), {"b": b})).rowcount == 1  # type: ignore[attr-defined]
    async with tx(rw_engine, [b]) as session:
        status = await scalar(session, "SELECT status FROM companies WHERE id = :b", b=b)
    assert status == "archived"

    with pytest.raises(DBAPIError) as info:
        async with tx(rw_engine, [b], admin=True) as session:
            await session.execute(
                text("UPDATE companies SET prefix = 'ZMIANA' WHERE id = :b"), {"b": b}
            )
    assert sqlstate(info.value) == "23001"


async def test_global_audit_chain_is_readable_by_app_admins_only(
    db_urls: DbUrls, world: World
) -> None:
    """Request transactions as built by ``current_user`` (ADR 0006 §6, ADR 0008 §6).

    The global chain holds data of every company (names, NIP, user e-mails): an auditor
    of company A reads and verifies A's chain, never the global one; an app admin reads
    the global chain (and no company chain without a company in scope).
    """
    app: FastAPI = create_app(make_settings(database_url=db_urls.rw))

    @app.get("/api/v1/_test/audit-visibility")
    async def _visibility(user: CurrentUserDep, session: SessionDep) -> dict[str, Any]:
        chains = await ids(session, "SELECT DISTINCT company_id FROM audit_log")
        verified: dict[str, Any] = {}
        for name, cid in (("global", None), ("a", world.a.id), ("b", world.b.id)):
            try:
                result = await audit_service.verify_chain(session, cid)
                verified[name] = result.ok
            except audit_service.AuditScopeError:
                verified[name] = "out_of_scope"
        return {"chains": sorted(str(c) for c in chains), "verified": verified}

    try:
        async with client_for(app) as client:
            auditor = (
                await client.get("/api/v1/_test/audit-visibility", headers=auth(world.auditor))
            ).json()
            admin = (
                await client.get("/api/v1/_test/audit-visibility", headers=auth(world.admin))
            ).json()
            outsider = (
                await client.get("/api/v1/_test/audit-visibility", headers=auth(world.outsider))
            ).json()
    finally:
        await app.state.db.dispose()

    assert auditor == {
        "chains": [str(world.a.id)],
        "verified": {"global": "out_of_scope", "a": True, "b": "out_of_scope"},
    }
    assert admin == {
        "chains": ["None"],
        "verified": {"global": True, "a": "out_of_scope", "b": "out_of_scope"},
    }
    assert outsider == {
        "chains": [str(world.b.id)],
        "verified": {"global": "out_of_scope", "a": "out_of_scope", "b": True},
    }
