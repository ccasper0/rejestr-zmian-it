"""Dictionaries and CI inventory at the database level (migration 0006, ADR 0011).

Runs as ``app_rw`` with explicit transaction scopes, WITHOUT the services: it proves what
the database alone enforces (formats, two-level categories, immutable codes, unique CI
identifiers per company regardless of letter case, grants, RLS).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db import apply_company_scope
from tests.factories import World

pytestmark = pytest.mark.db

INSUFFICIENT_PRIVILEGE = "42501"
RESTRICT_VIOLATION = "23001"
UNIQUE_VIOLATION = "23505"
CHECK_VIOLATION = "23514"
FOREIGN_KEY_VIOLATION = "23503"


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@asynccontextmanager
async def tx(
    engine: AsyncEngine, company_ids: Sequence[UUID] = (), *, admin: bool = False
) -> AsyncIterator[AsyncSession]:
    """One scoped transaction, rolled back at the end (no side effects)."""
    async with AsyncSession(engine) as session:
        await session.begin()
        await apply_company_scope(session, company_ids, admin_scope=admin)
        try:
            yield session
        finally:
            await session.rollback()


async def fails(
    engine: AsyncEngine,
    statements: Sequence[tuple[str, dict[str, Any]]],
    company_ids: Sequence[UUID] = (),
    *,
    admin: bool = False,
) -> str | None:
    """SQLSTATE of the first failing statement (``None`` when all succeed)."""
    try:
        async with tx(engine, company_ids, admin=admin) as session:
            for sql, params in statements:
                await session.execute(text(sql), params)
    except DBAPIError as exc:
        return sqlstate(exc)
    return None


def code() -> str:
    return "TST-" + uuid4().hex[:8].upper()


INSERT_CATEGORY = (
    "INSERT INTO change_categories (id, code, name, parent_id, requires_approval, default_risk) "
    "VALUES (:id, :code, 'Kategoria', :parent, true, 'medium')"
)
INSERT_CI_TYPE = "INSERT INTO ci_types (id, code, name) VALUES (:id, :code, 'Typ')"
INSERT_CI = (
    "INSERT INTO configuration_items (company_id, ci_type_id, identifier, name) "
    "VALUES (:c, :t, :i, 'Obiekt')"
)


# --------------------------------------------------------------------------- categories


async def test_category_hierarchy_has_two_levels(rw_engine: AsyncEngine) -> None:
    root, child, grandchild = uuid4(), uuid4(), uuid4()
    statements = [
        (INSERT_CATEGORY, {"id": root, "code": code(), "parent": None}),
        (INSERT_CATEGORY, {"id": child, "code": code(), "parent": root}),
    ]
    assert await fails(rw_engine, statements, admin=True) is None
    deeper = [*statements, (INSERT_CATEGORY, {"id": grandchild, "code": code(), "parent": child})]
    assert await fails(rw_engine, deeper, admin=True) == CHECK_VIOLATION
    own_parent = [(INSERT_CATEGORY, {"id": root, "code": code(), "parent": root})]
    assert await fails(rw_engine, own_parent, admin=True) in (
        CHECK_VIOLATION,
        FOREIGN_KEY_VIOLATION,
    )


@pytest.mark.parametrize(
    "update",
    [
        "UPDATE change_categories SET code = 'TST-ZMIANA' WHERE id = :child",
        "UPDATE change_categories SET parent_id = :other WHERE id = :child",
    ],
)
async def test_category_code_and_parent_are_immutable(rw_engine: AsyncEngine, update: str) -> None:
    root, other, child = uuid4(), uuid4(), uuid4()
    statements = [
        (INSERT_CATEGORY, {"id": root, "code": code(), "parent": None}),
        (INSERT_CATEGORY, {"id": other, "code": code(), "parent": None}),
        (INSERT_CATEGORY, {"id": child, "code": code(), "parent": root}),
        (update, {"child": child, "other": other} if ":other" in update else {"child": child}),
    ]
    assert await fails(rw_engine, statements, admin=True) == RESTRICT_VIOLATION


@pytest.mark.parametrize("bad", ["acc", "A", "ACC_1", "-ACC", "ACC-", "ĄCC", "A" * 33])
async def test_category_code_format(rw_engine: AsyncEngine, bad: str) -> None:
    statements = [(INSERT_CATEGORY, {"id": uuid4(), "code": bad, "parent": None})]
    assert await fails(rw_engine, statements, admin=True) == CHECK_VIOLATION


async def test_category_code_unique_and_risk_values(rw_engine: AsyncEngine) -> None:
    same = code()
    duplicate = [
        (INSERT_CATEGORY, {"id": uuid4(), "code": same, "parent": None}),
        (INSERT_CATEGORY, {"id": uuid4(), "code": same, "parent": None}),
    ]
    assert await fails(rw_engine, duplicate, admin=True) == UNIQUE_VIOLATION
    bad_risk = [
        (
            "INSERT INTO change_categories (code, name, requires_approval, default_risk) "
            "VALUES (:code, 'X', true, 'critical')",
            {"code": code()},
        )
    ]
    assert await fails(rw_engine, bad_risk, admin=True) == CHECK_VIOLATION


# --------------------------------------------------------------------------- CI types


async def test_ci_type_code_format_unique_and_immutable(rw_engine: AsyncEngine) -> None:
    same = "t_" + uuid4().hex[:8]
    assert (
        await fails(rw_engine, [(INSERT_CI_TYPE, {"id": uuid4(), "code": "Server"})], admin=True)
        == CHECK_VIOLATION
    )
    duplicate = [
        (INSERT_CI_TYPE, {"id": uuid4(), "code": same}),
        (INSERT_CI_TYPE, {"id": uuid4(), "code": same}),
    ]
    assert await fails(rw_engine, duplicate, admin=True) == UNIQUE_VIOLATION
    type_id = uuid4()
    immutable = [
        (INSERT_CI_TYPE, {"id": type_id, "code": same}),
        ("UPDATE ci_types SET code = 'inny_kod' WHERE id = :id", {"id": type_id}),
    ]
    assert await fails(rw_engine, immutable, admin=True) == RESTRICT_VIOLATION


# --------------------------------------------------------------------------- dictionaries: writes


async def test_dictionaries_are_written_only_on_the_admin_path(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Defence in depth (ADR 0011): readable by everybody, writable only on the admin path."""
    for statement in (
        (INSERT_CATEGORY, {"id": uuid4(), "code": code(), "parent": None}),
        (INSERT_CI_TYPE, {"id": uuid4(), "code": "t_" + uuid4().hex[:8]}),
    ):
        assert await fails(rw_engine, [statement], [world.a.id]) == INSUFFICIENT_PRIVILEGE
    async with tx(rw_engine, [world.a.id]) as session:
        for sql, row_id in (
            ("UPDATE change_categories SET name = name WHERE id = :id", world.category.id),
            ("UPDATE ci_types SET name = name WHERE id = :id", world.ci_type.id),
        ):
            result = await session.execute(text(sql), {"id": row_id})
            assert result.rowcount == 0  # type: ignore[attr-defined]
        visible = (
            await session.execute(
                text("SELECT count(*) FROM change_categories WHERE id = :id"),
                {"id": world.category.id},
            )
        ).scalar_one()
    assert visible == 1  # reading needs no admin path


async def test_app_rw_privileges_on_inventory_tables(rw_engine: AsyncEngine) -> None:
    """Nothing is deleted except company_categories rows (a PUT removes availability;
    the removal is in the audit log). No TRUNCATE anywhere."""
    privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
    tables = ("change_categories", "ci_types", "company_categories", "configuration_items")
    granted = set()
    async with rw_engine.connect() as conn:
        for table in tables:
            for privilege in privileges:
                if (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": table, "p": privilege},
                    )
                ).scalar_one():
                    granted.add((table, privilege))
        owners = set(
            (
                await conn.execute(
                    text("SELECT tableowner FROM pg_tables WHERE tablename = ANY (:t)"),
                    {"t": list(tables)},
                )
            ).scalars()
        )
    assert owners == {"app_owner"}
    assert granted == {
        *((t, p) for t in tables for p in ("SELECT", "INSERT", "UPDATE")),
        ("company_categories", "DELETE"),
    }


# --------------------------------------------------------------------------- CI


async def test_ci_identifier_unique_per_company_regardless_of_case(
    rw_engine: AsyncEngine, world: World
) -> None:
    a, b, t = world.a.id, world.b.id, world.ci_type.id
    same_company = [
        (INSERT_CI, {"c": a, "t": t, "i": "FW-UNIQ-01"}),
        (INSERT_CI, {"c": a, "t": t, "i": "fw-uniq-01"}),
    ]
    assert await fails(rw_engine, same_company, [a]) == UNIQUE_VIOLATION
    other_company = [
        (INSERT_CI, {"c": a, "t": t, "i": "FW-UNIQ-02"}),
        (INSERT_CI, {"c": b, "t": t, "i": "FW-UNIQ-02"}),
    ]
    assert await fails(rw_engine, other_company, [a, b]) is None


async def test_ci_company_is_immutable(rw_engine: AsyncEngine, world: World) -> None:
    statements = [
        (
            "UPDATE configuration_items SET company_id = :b WHERE id = :id",
            {"b": world.b.id, "id": world.ci_a.id},
        )
    ]
    assert await fails(rw_engine, statements, [world.a.id, world.b.id]) == RESTRICT_VIOLATION


async def test_ci_rls_isolates_companies(rw_engine: AsyncEngine, world: World) -> None:
    a, b, t = world.a.id, world.b.id, world.ci_type.id
    # Writing into a company outside the scope violates WITH CHECK.
    assert (
        await fails(rw_engine, [(INSERT_CI, {"c": b, "t": t, "i": "OBCY-1"})], [a])
        == INSUFFICIENT_PRIVILEGE
    )
    async with tx(rw_engine, [a]) as session:
        visible = set(
            (await session.execute(text("SELECT DISTINCT company_id FROM configuration_items")))
            .scalars()
            .all()
        )
        updated = await session.execute(
            text("UPDATE configuration_items SET name = 'x' WHERE id = :id"),
            {"id": world.ci_b.id},
        )
    assert visible == {a}
    assert updated.rowcount == 0  # type: ignore[attr-defined]
    # The admin flag alone does not open CI of other companies: only the scope does.
    async with tx(rw_engine, [], admin=True) as session:
        admin_visible = (
            await session.execute(text("SELECT count(*) FROM configuration_items"))
        ).scalar_one()
    assert admin_visible == 0


async def test_company_categories_written_only_on_the_admin_path(
    rw_engine: AsyncEngine, world: World
) -> None:
    a, b = world.a.id, world.b.id
    insert = (
        "INSERT INTO company_categories (company_id, category_id) VALUES (:c, :k)",
        {"c": a, "k": world.category.id},
    )
    # Member scope (no admin path): denied, even within the own company.
    assert await fails(rw_engine, [insert], [a]) == INSUFFICIENT_PRIVILEGE
    # Admin path, but a company outside the scope: denied.
    foreign = (insert[0], {"c": b, "k": world.category.id})
    assert await fails(rw_engine, [foreign], [a], admin=True) == INSUFFICIENT_PRIVILEGE
    # Admin path within the scope: allowed; duplicates rejected.
    assert await fails(rw_engine, [insert], [a], admin=True) is None
    assert await fails(rw_engine, [insert, insert], [a], admin=True) == UNIQUE_VIOLATION


async def test_services_cannot_reach_another_company_even_if_misused(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Defence in depth: the services called with company B inside a transaction scoped to
    company A (an application bug) see nothing and change nothing - RLS alone."""
    from app.errors import ProblemError
    from app.services import company_categories, configuration_items
    from tests.factories import SYSTEM

    async with tx(rw_engine, [world.a.id]) as session:
        rows, total = await configuration_items.list_items(session, world.b.id, limit=100, offset=0)
        item = await configuration_items.get_item(session, world.b.id, world.ci_b.id)
        with pytest.raises(ProblemError) as info:
            await configuration_items.update_item(
                session, actor=SYSTEM, company=world.b, ci_id=world.ci_b.id, changes={"name": "x"}
            )
        available = await company_categories.list_company_categories(session, world.b.id)
    assert (rows, total, item, available) == ([], 0, None, [])
    assert (info.value.status, info.value.code) == (404, "ci.not_found")

    # Company categories are written on the admin path only: a member scope cannot even
    # lock the company row (404), with or without the company in scope.
    async with tx(rw_engine, [world.a.id]) as session:
        with pytest.raises(ProblemError) as info:
            await company_categories.set_company_categories(
                session,
                actor=SYSTEM,
                company_id=world.a.id,
                assignments=[company_categories.Assignment(world.category.id)],
            )
    assert (info.value.status, info.value.code) == (404, "company.not_found")


async def test_ci_of_an_archived_company_cannot_be_written(
    rw_engine: AsyncEngine, world: World
) -> None:
    """Trigger company_must_be_active (migration 0007), bypassing the services: no INSERT
    or UPDATE of CI in an archived company, for any scope."""
    from tests.factories import make_ci, make_company

    company = await make_company(rw_engine)
    ci = await make_ci(rw_engine, company, world.ci_type)
    async with AsyncSession(rw_engine) as session, session.begin():
        await apply_company_scope(session, [company.id], admin_scope=True)
        await session.execute(
            text("UPDATE companies SET status = 'archived' WHERE id = :c"), {"c": company.id}
        )
    for statement in (
        (INSERT_CI, {"c": company.id, "t": world.ci_type.id, "i": "ARCH-1"}),
        ("UPDATE configuration_items SET name = 'x' WHERE id = :id", {"id": ci.id}),
    ):
        for admin in (False, True):
            assert await fails(rw_engine, [statement], [company.id], admin=admin) == (
                RESTRICT_VIOLATION
            )
    # Active companies are unaffected.
    ok = (INSERT_CI, {"c": world.a.id, "t": world.ci_type.id, "i": "ACTIVE-1"})
    assert await fails(rw_engine, [ok], [world.a.id]) is None
