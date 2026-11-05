"""Real roles from deploy/postgres/init/roles.psql + migrations (CLAUDE.md 6.3, ADR 0006)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db import apply_company_scope
from app.models import Base
from tests.conftest import DbUrls, run_alembic

pytestmark = pytest.mark.db

INSUFFICIENT_PRIVILEGE = "42501"


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


async def test_app_rw_is_neither_superuser_nor_bypassrls(rw_engine: AsyncEngine) -> None:
    async with rw_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one()
    assert row.current_user == "app_rw"
    assert row.rolsuper is False
    assert row.rolbypassrls is False
    assert row.rolcreaterole is False
    assert row.rolcreatedb is False


async def test_app_owner_is_not_superuser(owner_engine: AsyncEngine) -> None:
    async with owner_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    assert (row.rolsuper, row.rolbypassrls) == (False, False)


async def test_audit_tables_owned_by_app_owner_with_rls_enabled(rw_engine: AsyncEngine) -> None:
    async with rw_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT c.relname, pg_get_userbyid(c.relowner) AS owner, c.relrowsecurity "
                    "FROM pg_class c WHERE c.relname IN ('audit_log', 'audit_chain_heads')"
                )
            )
        ).all()
    assert {(r.relname, r.owner, r.relrowsecurity) for r in rows} == {
        ("audit_log", "app_owner", True),
        ("audit_chain_heads", "app_owner", True),
    }


async def test_app_rw_privileges_on_audit_tables(rw_engine: AsyncEngine) -> None:
    privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
    async with rw_engine.connect() as conn:
        granted = {}
        for table in ("audit_log", "audit_chain_heads", "alembic_version"):
            for privilege in privileges:
                granted[(table, privilege)] = (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": table, "p": privilege},
                    )
                ).scalar_one()
    allowed = {
        ("audit_log", "SELECT"),
        ("audit_log", "INSERT"),
        ("audit_chain_heads", "SELECT"),
        ("audit_chain_heads", "INSERT"),
        ("audit_chain_heads", "UPDATE"),
        ("alembic_version", "SELECT"),
    }
    assert {key for key, value in granted.items() if value} == allowed


async def test_app_rw_privileges_on_auth_event_tables(rw_engine: AsyncEngine) -> None:
    """ADR 0010: login rows are immutable (purged only); failure counters are updated."""
    privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
    async with rw_engine.connect() as conn:
        granted = set()
        owners = set()
        for table in ("auth_logins", "auth_failure_windows"):
            owners.add(
                (
                    await conn.execute(
                        text("SELECT tableowner FROM pg_tables WHERE tablename = :t"),
                        {"t": table},
                    )
                ).scalar_one()
            )
            for privilege in privileges:
                if (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": table, "p": privilege},
                    )
                ).scalar_one():
                    granted.add((table, privilege))
    assert owners == {"app_owner"}
    assert granted == {
        ("auth_logins", "SELECT"),
        ("auth_logins", "INSERT"),
        ("auth_logins", "DELETE"),
        ("auth_failure_windows", "SELECT"),
        ("auth_failure_windows", "INSERT"),
        ("auth_failure_windows", "UPDATE"),
        ("auth_failure_windows", "DELETE"),
    }


async def test_app_rw_privileges_on_local_account_tables(rw_engine: AsyncEngine) -> None:
    """ADR 0018: no DELETE of credentials, UPDATE only of the mutable columns."""
    privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
    tables = ("user_credentials", "auth_sessions", "auth_refresh_tokens")
    async with rw_engine.connect() as conn:
        granted = set()
        for table in tables:
            for privilege in privileges:
                if (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": table, "p": privilege},
                    )
                ).scalar_one():
                    granted.add((table, privilege))
        columns = set(
            (
                await conn.execute(
                    text(
                        "SELECT table_name || '.' || column_name FROM "
                        "information_schema.column_privileges WHERE grantee = 'app_rw' "
                        "AND privilege_type = 'UPDATE' AND table_name = ANY(:t)"
                    ),
                    {"t": list(tables)},
                )
            )
            .scalars()
            .all()
        )
    assert granted == {
        ("user_credentials", "SELECT"),
        ("user_credentials", "INSERT"),
        ("auth_sessions", "SELECT"),
        ("auth_sessions", "INSERT"),
        ("auth_sessions", "DELETE"),
        ("auth_refresh_tokens", "SELECT"),
        ("auth_refresh_tokens", "INSERT"),
        ("auth_refresh_tokens", "DELETE"),
    }
    assert columns == {
        "user_credentials.password_hash",
        "user_credentials.password_changed_at",
        "user_credentials.must_change_password",
        "user_credentials.failed_attempts",
        "user_credentials.locked_until",
        "user_credentials.temp_password_expires_at",
        "user_credentials.updated_at",
        "auth_sessions.refreshed_at",
        "auth_sessions.revoked_at",
        "auth_sessions.revoke_reason",
        "auth_sessions.updated_at",
        "auth_refresh_tokens.rotated_at",
        "auth_refresh_tokens.updated_at",
    }


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE alembic_version SET version_num = 'hacked'",
        "INSERT INTO alembic_version VALUES ('hacked')",
        "DELETE FROM alembic_version",
        "TRUNCATE alembic_version",
    ],
)
async def test_app_rw_cannot_write_alembic_version(rw_engine: AsyncEngine, statement: str) -> None:
    async with rw_engine.connect() as conn:
        assert (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
        with pytest.raises(DBAPIError) as info:
            await conn.execute(text(statement))
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE


async def test_app_rw_cannot_disable_triggers_via_replication_role(
    rw_engine: AsyncEngine,
) -> None:
    async with rw_engine.connect() as conn:
        with pytest.raises(DBAPIError) as info:
            await conn.execute(text("SET session_replication_role = replica"))
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE


async def test_app_rw_cannot_alter_audit_tables(rw_engine: AsyncEngine) -> None:
    async with rw_engine.connect() as conn:
        with pytest.raises(DBAPIError) as info:
            await conn.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE


async def test_models_match_migrations(owner_engine: AsyncEngine) -> None:
    def _diff(conn: Connection) -> list[object]:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        return list(compare_metadata(ctx, Base.metadata))

    async with owner_engine.connect() as conn:
        assert await conn.run_sync(_diff) == []


ALLOW_LOSS = ("-x", "allow_audit_data_loss=yes", "-x", "allow_credential_loss=yes")


async def test_downgrade_guarded_and_reversible(db_urls: DbUrls, rw_engine: AsyncEngine) -> None:
    company = uuid4()
    async with AsyncSession(rw_engine) as session, session.begin():
        # A first entry of a fresh chain, written by app_rw directly (the database-side
        # rules accept it; the hash value itself is irrelevant here).
        await apply_company_scope(session, [company])
        await session.execute(
            text(
                "INSERT INTO audit_log (company_id, seq, occurred_at, actor_display, "
                "actor_roles, request_id, entity_type, action, diff, context, prev_hash, hash) "
                "VALUES (:c, 1, clock_timestamp(), 'system', '{}', gen_random_uuid(), 'audit', "
                "'verify', '{}', '{}', repeat('0', 64), repeat('1', 64))"
            ),
            {"c": company},
        )

    # app_rw is not the owner: downgrade refuses.
    denied = run_alembic(db_urls.rw, "downgrade", "base")
    assert denied.returncode != 0
    assert "must run as the table owner" in denied.stderr

    # The report exports (0009) guard their rows the same way (tested separately): drop
    # them first, so this refusal is the one of the audit core.
    reports_dropped = run_alembic(db_urls.owner, *ALLOW_LOSS, "downgrade", "0008")
    assert reports_dropped.returncode == 0, reports_dropped.stderr

    # Owner, but the log is not empty and data loss was not explicitly allowed.
    refused = run_alembic(db_urls.owner, "downgrade", "base")
    assert refused.returncode != 0
    assert "audit_log is not empty" in refused.stderr

    try:
        done = run_alembic(db_urls.owner, *ALLOW_LOSS, "downgrade", "base")
        assert done.returncode == 0, done.stderr
        async with rw_engine.connect() as conn:
            remaining = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM pg_class WHERE relname IN "
                        "('audit_log', 'audit_chain_heads', 'users', 'companies', "
                        "'company_memberships', 'auth_logins', 'auth_failure_windows', "
                        "'change_categories', 'ci_types', 'company_categories', "
                        "'configuration_items', 'changes', 'change_items', "
                        "'change_ci_consents', 'change_comments', 'attachments', "
                        "'number_sequences', 'report_exports', 'report_number_sequences', "
                        "'user_credentials', 'auth_sessions', 'auth_refresh_tokens', "
                        "'uq_users_email_lower')"
                    )
                )
            ).scalar_one()
            functions = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM pg_proc WHERE proname IN ('app_company_ids', "
                        "'app_global_audit_read', 'app_user_id', 'app_admin_scope', "
                        "'audit_log_reject_modification', "
                        "'audit_log_check_append', 'audit_chain_heads_check', "
                        "'companies_prefix_immutable', 'change_categories_guard', "
                        "'ci_types_code_immutable', 'company_id_immutable', "
                        "'company_must_be_active', 'reject_modification', "
                        "'app_change_action', 'changes_guard', 'change_items_guard', "
                        "'number_sequences_guard', 'report_exports_guard', "
                        "'report_number_sequences_guard', 'auth_sessions_guard', "
                        "'auth_refresh_tokens_guard')"
                    )
                )
            ).scalar_one()
        assert (remaining, functions) == (0, 0)
    finally:
        upgraded = run_alembic(db_urls.owner, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr


async def test_report_exports_downgrade_refuses_to_drop_rows(
    db_urls: DbUrls, rw_engine: AsyncEngine
) -> None:
    """Migration 0009: a non-empty ``report_exports`` (the register of exports) is never
    dropped silently - only with ``-x allow_audit_data_loss=yes`` (ADR 0017 §14)."""
    from app.permissions import Role
    from tests.factories import make_report, make_world

    world = await make_world(rw_engine)
    await make_report(rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}})

    refused = run_alembic(db_urls.owner, "-x", "allow_credential_loss=yes", "downgrade", "0008")
    assert refused.returncode != 0
    assert "report_exports is not empty" in refused.stderr
    async with rw_engine.connect() as conn:
        assert (
            await conn.execute(text("SELECT to_regclass('report_exports') IS NOT NULL"))
        ).scalar_one()
    try:
        done = run_alembic(db_urls.owner, *ALLOW_LOSS, "downgrade", "0008")
        assert done.returncode == 0, done.stderr
        async with rw_engine.connect() as conn:
            assert (
                await conn.execute(text("SELECT to_regclass('report_exports') IS NULL"))
            ).scalar_one()
    finally:
        upgraded = run_alembic(db_urls.owner, "upgrade", "head")
        assert upgraded.returncode == 0, upgraded.stderr


async def test_temp_password_expiry_migration_backfills_and_reverts(
    db_urls: DbUrls, owner_engine: AsyncEngine
) -> None:
    """Migration 0011 (ADR 0018 §12 p. 4): existing temporary passwords get the default
    deadline (password_changed_at + 168 h); the downgrade drops the column."""
    suffix = uuid4().hex[:10]
    down = run_alembic(db_urls.owner, "downgrade", "0010")
    assert down.returncode == 0, down.stderr
    try:
        async with owner_engine.begin() as conn:
            user_ids = []
            for must_change in (True, False):
                user_id = (
                    await conn.execute(
                        text(
                            "INSERT INTO users (external_id, email, display_name, "
                            "is_app_admin, is_active) VALUES (:x, :e, 'Migracja', false, true) "
                            "RETURNING id"
                        ),
                        {
                            "x": f"local:{suffix}-{must_change}",
                            "e": f"m{must_change}{suffix}@example.com",
                        },
                    )
                ).scalar_one()
                await conn.execute(
                    text(
                        "INSERT INTO user_credentials (user_id, password_hash, "
                        "password_changed_at, must_change_password) VALUES "
                        "(:u, '$argon2id$x', timestamptz '2026-11-01 10:00:00+00', :m)"
                    ),
                    {"u": user_id, "m": must_change},
                )
                user_ids.append(user_id)
    finally:
        up = run_alembic(db_urls.owner, "upgrade", "head")
        assert up.returncode == 0, up.stderr
    async with owner_engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT must_change_password, "
                    "to_char(temp_password_expires_at AT TIME ZONE 'UTC', "
                    "'YYYY-MM-DD HH24:MI') AS deadline "
                    "FROM user_credentials WHERE user_id = ANY(:u) ORDER BY must_change_password"
                ),
                {"u": user_ids},
            )
        ).all()
    assert [(r.must_change_password, r.deadline) for r in rows] == [
        (False, None),
        (True, "2026-11-08 10:00"),
    ]
