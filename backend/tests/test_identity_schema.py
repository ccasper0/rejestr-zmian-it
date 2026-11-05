"""Migration 0002: users, companies, company_memberships (CLAUDE.md 4.1, 5, 6.3).

Database-level guarantees only; service behaviour is tested in the API tests.

Since migration 0003 the identity tables have Row-Level Security: statements here run on
the explicit admin path with the touched companies in scope (``admin_tx``), so that the
constraints themselves are exercised. RLS is tested in ``tests/test_rls.py``.
"""

from __future__ import annotations

import secrets
import string
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

pytestmark = pytest.mark.db

INSUFFICIENT_PRIVILEGE = "42501"
CHECK_VIOLATION = "23514"
UNIQUE_VIOLATION = "23505"
RESTRICT_VIOLATION = "23001"
FK_VIOLATION = "23503"


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


def random_prefix(length: int = 8) -> str:
    return "".join(secrets.choice(string.ascii_uppercase) for _ in range(length))


@asynccontextmanager
async def admin_tx(
    engine: AsyncEngine, scope: Sequence[UUID] = (), *, commit: bool = True
) -> AsyncIterator[AsyncConnection]:
    """One transaction on the explicit admin path with ``scope`` as the company scope."""
    async with engine.connect() as conn:
        await conn.execute(
            text(
                "SELECT set_config('app.admin_scope', 'on', true), "
                "set_config('app.company_ids', :ids, true)"
            ),
            {"ids": "{" + ",".join(str(c) for c in scope) + "}"},
        )
        yield conn
        if commit:
            await conn.commit()


async def insert_company(engine: AsyncEngine, prefix: str | None = None, **values: object) -> UUID:
    params = {
        "name": f"Spółka {uuid4()}",
        "prefix": random_prefix() if prefix is None else prefix,
        **values,
    }
    columns = ", ".join(params)
    binds = ", ".join(f":{k}" for k in params)
    async with admin_tx(engine) as conn:
        result = await conn.execute(
            text(f"INSERT INTO companies ({columns}) VALUES ({binds}) RETURNING id"),  # noqa: S608
            params,
        )
        return UUID(str(result.scalar_one()))


async def insert_user(engine: AsyncEngine) -> UUID:
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO users (external_id, email, display_name) "
                "VALUES (:e, :m, 'Jan Testowy') RETURNING id"
            ),
            {"e": f"ext-{uuid4()}", "m": f"{uuid4().hex}@example.com"},
        )
        return UUID(str(result.scalar_one()))


async def expect_sqlstate(
    engine: AsyncEngine,
    statement: str,
    state: str,
    *,
    scope: Sequence[UUID] = (),
    **params: object,
) -> None:
    async with admin_tx(engine, scope, commit=False) as conn:
        with pytest.raises(DBAPIError) as info:
            await conn.execute(text(statement), params)
    assert sqlstate(info.value) == state, info.value


async def test_company_defaults(rw_engine: AsyncEngine) -> None:
    company = await insert_company(rw_engine)
    async with admin_tx(rw_engine, commit=False) as conn:
        row = (
            await conn.execute(text("SELECT * FROM companies WHERE id = :id"), {"id": company})
        ).one()
    assert row.status == "active"
    assert row.is_ksc_entity is False
    assert row.tax_id is None
    assert row.default_approver_id is None
    assert row.created_at.utcoffset().total_seconds() == 0
    assert row.updated_at is not None


@pytest.mark.parametrize("prefix", ["A", "ABCDEFGHI", "alfa", "AL1", "AŁFA", "AL-FA", ""])
async def test_prefix_format_enforced(rw_engine: AsyncEngine, prefix: str) -> None:
    with pytest.raises(DBAPIError) as info:
        await insert_company(rw_engine, prefix=prefix)
    assert sqlstate(info.value) == CHECK_VIOLATION


async def test_prefix_and_name_unique(rw_engine: AsyncEngine) -> None:
    prefix = random_prefix()
    await insert_company(rw_engine, prefix=prefix, name=f"Unikalna {prefix}")
    for kwargs in ({"prefix": prefix}, {"name": f"Unikalna {prefix}"}):
        with pytest.raises(DBAPIError) as info:
            await insert_company(rw_engine, **kwargs)  # type: ignore[arg-type]
        assert sqlstate(info.value) == UNIQUE_VIOLATION


async def test_status_values(rw_engine: AsyncEngine) -> None:
    company = await insert_company(rw_engine)
    await expect_sqlstate(
        rw_engine,
        "UPDATE companies SET status = 'deleted' WHERE id = :id",
        CHECK_VIOLATION,
        scope=[company],
        id=company,
    )
    async with admin_tx(rw_engine, [company]) as conn:
        await conn.execute(
            text("UPDATE companies SET status = 'archived' WHERE id = :id"), {"id": company}
        )


@pytest.mark.parametrize("as_owner", [False, True])
async def test_prefix_immutable_in_database(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine, as_owner: bool
) -> None:
    engine = owner_engine if as_owner else rw_engine
    company = await insert_company(engine)
    await expect_sqlstate(
        engine,
        "UPDATE companies SET prefix = :p WHERE id = :id",
        RESTRICT_VIOLATION,
        scope=[company],
        p=random_prefix(),
        id=company,
    )
    # Other columns stay editable (same value for prefix is not a change).
    async with admin_tx(engine, [company]) as conn:
        await conn.execute(
            text("UPDATE companies SET name = :n, prefix = prefix WHERE id = :id"),
            {"n": f"Nowa {uuid4()}", "id": company},
        )


async def test_app_rw_cannot_delete_companies_or_users(rw_engine: AsyncEngine) -> None:
    company = await insert_company(rw_engine)
    user = await insert_user(rw_engine)
    await expect_sqlstate(
        rw_engine, "DELETE FROM companies WHERE id = :id", INSUFFICIENT_PRIVILEGE, id=company
    )
    await expect_sqlstate(
        rw_engine, "DELETE FROM users WHERE id = :id", INSUFFICIENT_PRIVILEGE, id=user
    )


async def test_app_rw_privileges_on_identity_tables(rw_engine: AsyncEngine) -> None:
    privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
    granted = set()
    async with rw_engine.connect() as conn:
        for table in ("users", "companies", "company_memberships"):
            for privilege in privileges:
                ok = (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": table, "p": privilege},
                    )
                ).scalar_one()
                if ok:
                    granted.add((table, privilege))
    assert granted == {
        ("users", "SELECT"),
        ("users", "INSERT"),
        ("users", "UPDATE"),
        ("companies", "SELECT"),
        ("companies", "INSERT"),
        ("companies", "UPDATE"),
        ("company_memberships", "SELECT"),
        ("company_memberships", "INSERT"),
        ("company_memberships", "UPDATE"),
        ("company_memberships", "DELETE"),
    }


async def test_external_id_unique(rw_engine: AsyncEngine) -> None:
    external = f"ext-{uuid4()}"
    sql = "INSERT INTO users (external_id, email, display_name) VALUES (:e, 'a@example.com', 'A')"
    async with rw_engine.begin() as conn:
        await conn.execute(text(sql), {"e": external})
    await expect_sqlstate(rw_engine, sql, UNIQUE_VIOLATION, e=external)


async def test_membership_constraints(rw_engine: AsyncEngine) -> None:
    company = await insert_company(rw_engine)
    user = await insert_user(rw_engine)
    missing_company = uuid4()
    scope = [company, missing_company]
    sql = "INSERT INTO company_memberships (user_id, company_id, role) VALUES (:u, :c, :r)"
    async with admin_tx(rw_engine, scope) as conn:
        # Several roles in one company are allowed.
        await conn.execute(text(sql), {"u": user, "c": company, "r": "editor"})
        await conn.execute(text(sql), {"u": user, "c": company, "r": "approver"})
    await expect_sqlstate(
        rw_engine, sql, UNIQUE_VIOLATION, scope=scope, u=user, c=company, r="editor"
    )
    # app_admin is a user flag, never a membership role.
    for role in ("app_admin", "owner", ""):
        await expect_sqlstate(
            rw_engine, sql, CHECK_VIOLATION, scope=scope, u=user, c=company, r=role
        )
    await expect_sqlstate(
        rw_engine, sql, FK_VIOLATION, scope=scope, u=uuid4(), c=company, r="viewer"
    )
    await expect_sqlstate(
        rw_engine, sql, FK_VIOLATION, scope=scope, u=user, c=missing_company, r="viewer"
    )


async def test_default_approver_must_be_a_user(rw_engine: AsyncEngine) -> None:
    with pytest.raises(DBAPIError) as info:
        await insert_company(rw_engine, default_approver_id=uuid4())
    assert sqlstate(info.value) == FK_VIOLATION
    approver = await insert_user(rw_engine)
    await insert_company(rw_engine, default_approver_id=approver)
