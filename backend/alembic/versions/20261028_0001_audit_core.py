"""Audit core: audit_log, audit_chain_heads, protection triggers, RLS, grants.

CLAUDE.md 6.1-6.3 and 7; decisions in docs/decisions/0006-audit-chain-storage.md.

Revision ID: 0001
Revises:
Create Date: 2026-10-28

Runs as ``app_owner``. ``downgrade`` refuses to run as any other role and refuses to drop
a non-empty ``audit_log`` unless explicitly told so (``-x allow_audit_data_loss=yes``).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

HEX64 = "^[0-9a-f]{64}$"

# --------------------------------------------------------------------------- SQL blocks

# asyncpg executes one statement per call, hence lists of statements.

RLS_HELPERS = [
    # Companies of the current transaction (SET LOCAL app.company_ids /
    # set_config(..., true)). Missing or empty setting = no company: an unscoped
    # connection sees nothing.
    """
    CREATE FUNCTION app_company_ids() RETURNS uuid[]
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT COALESCE(NULLIF(current_setting('app.company_ids', true), ''), '{}')::uuid[] $$
    """,
    # Explicit, separate path for reading the global audit chain (app admin, auditor).
    """
    CREATE FUNCTION app_global_audit_read() RETURNS boolean
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT COALESCE(current_setting('app.audit_global_read', true), '') = 'on' $$
    """,
]

AUDIT_FUNCTIONS = [
    r"""CREATE FUNCTION audit_log_reject_modification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation',
              HINT = 'Audit entries can never be changed or removed (CLAUDE.md 6.3).';
END
$$
    """,
    r"""-- Defence in depth for the chain (the application computes hashes, the database
-- guarantees linearity): seq continues the chain and prev_hash equals the hash of the
-- previous entry; occurred_at comes from the database clock of this transaction.
-- SECURITY DEFINER so the lookup of the previous entry is not hidden by RLS.
CREATE FUNCTION audit_log_check_append() RETURNS trigger
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, public
    AS $$
DECLARE
    expected_prev text;
BEGIN
    IF NEW.occurred_at < now() OR NEW.occurred_at > clock_timestamp() THEN
        RAISE EXCEPTION 'audit_log.occurred_at must come from the database clock '
                        'of the current transaction'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.seq = 1 THEN
        expected_prev := repeat('0', 64);
    ELSIF NEW.company_id IS NULL THEN
        SELECT a.hash INTO expected_prev FROM public.audit_log a
         WHERE a.company_id IS NULL AND a.seq = NEW.seq - 1;
    ELSE
        SELECT a.hash INTO expected_prev FROM public.audit_log a
         WHERE a.company_id = NEW.company_id AND a.seq = NEW.seq - 1;
    END IF;
    IF expected_prev IS NULL OR NEW.prev_hash <> expected_prev THEN
        RAISE EXCEPTION 'audit chain violation: entry seq % does not continue its chain',
                        NEW.seq
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    r"""-- A chain head may only be created empty and may only advance by exactly one entry,
-- to an entry that exists. app_rw has no DELETE on heads.
CREATE FUNCTION audit_chain_heads_check() RETURNS trigger
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, public
    AS $$
DECLARE
    entry_hash text;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.last_seq <> 0 OR NEW.last_hash <> repeat('0', 64) THEN
            RAISE EXCEPTION 'audit chain head must start empty'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.id <> OLD.id
       OR NEW.created_at <> OLD.created_at THEN
        RAISE EXCEPTION 'audit chain head identity is immutable'
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.last_seq <> OLD.last_seq + 1 THEN
        RAISE EXCEPTION 'audit chain head may only advance by one entry (% -> %)',
                        OLD.last_seq, NEW.last_seq
            USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.company_id IS NULL THEN
        SELECT a.hash INTO entry_hash FROM public.audit_log a
         WHERE a.company_id IS NULL AND a.seq = NEW.last_seq;
    ELSE
        SELECT a.hash INTO entry_hash FROM public.audit_log a
         WHERE a.company_id = NEW.company_id AND a.seq = NEW.last_seq;
    END IF;
    IF entry_hash IS NULL OR entry_hash <> NEW.last_hash THEN
        RAISE EXCEPTION 'audit chain head must point to an existing entry'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION audit_log_reject_modification() FROM PUBLIC, app_rw",
    "REVOKE ALL ON FUNCTION audit_log_check_append() FROM PUBLIC, app_rw",
    "REVOKE ALL ON FUNCTION audit_chain_heads_check() FROM PUBLIC, app_rw",
]

AUDIT_TRIGGERS = [
    """
    CREATE TRIGGER audit_log_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_reject_modification()
    """,
    """
    CREATE TRIGGER audit_log_no_truncate
        BEFORE TRUNCATE ON audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION audit_log_reject_modification()
    """,
    """
    CREATE TRIGGER audit_log_append_only_chain
        BEFORE INSERT ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_check_append()
    """,
    """
    CREATE TRIGGER audit_chain_heads_guard
        BEFORE INSERT OR UPDATE ON audit_chain_heads
        FOR EACH ROW EXECUTE FUNCTION audit_chain_heads_check()
    """,
    """
    CREATE TRIGGER audit_chain_heads_no_delete
        BEFORE DELETE OR TRUNCATE ON audit_chain_heads
        FOR EACH STATEMENT EXECUTE FUNCTION audit_log_reject_modification()
    """,
]

# app_rw is not the owner and has no BYPASSRLS, so RLS applies to it. The owner
# (app_owner, migrations only) is deliberately not FORCEd (ADR 0006).
AUDIT_RLS = [
    "ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY audit_log_select ON audit_log FOR SELECT TO app_rw
        USING (company_id = ANY (app_company_ids())
               OR (company_id IS NULL AND app_global_audit_read()))
    """,
    # Global events (logins, failed logins, access denials, dictionaries) are written by
    # any user; company events only within the transaction's company scope.
    """
    CREATE POLICY audit_log_insert ON audit_log FOR INSERT TO app_rw
        WITH CHECK (company_id IS NULL OR company_id = ANY (app_company_ids()))
    """,
    "ALTER TABLE audit_chain_heads ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY audit_chain_heads_scope ON audit_chain_heads FOR ALL TO app_rw
        USING (company_id IS NULL OR company_id = ANY (app_company_ids()))
        WITH CHECK (company_id IS NULL OR company_id = ANY (app_company_ids()))
    """,
]

AUDIT_GRANTS = [
    "REVOKE ALL ON audit_log FROM app_rw",
    "GRANT SELECT, INSERT ON audit_log TO app_rw",
    "REVOKE ALL ON SEQUENCE audit_log_id_seq FROM app_rw",
    "GRANT USAGE ON SEQUENCE audit_log_id_seq TO app_rw",
    "REVOKE ALL ON audit_chain_heads FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON audit_chain_heads TO app_rw",
    # Default privileges gave app_rw DML on alembic_version (created by Alembic as
    # app_owner before this migration). The application may only read it.
    "REVOKE ALL ON alembic_version FROM app_rw",
    "GRANT SELECT ON alembic_version TO app_rw",
]


def _execute_all(statements: list[str]) -> None:
    for statement in statements:
        op.execute(statement)


def upgrade() -> None:
    _execute_all(RLS_HELPERS)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # No FK (ADR 0006): NULL = global chain; companies are never deleted anyway.
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("seq", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        # No FK (ADR 0006): NULL = 'system'; actor_display is the frozen name.
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_display", sa.Text(), nullable=False),
        sa.Column("actor_roles", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("diff", postgresql.JSONB(), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("prev_hash", sa.CHAR(64), nullable=False),
        sa.Column("hash", sa.CHAR(64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
        sa.UniqueConstraint(
            "company_id",
            "seq",
            name=op.f("uq_audit_log_company_id_seq"),
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint("seq >= 1", name=op.f("ck_audit_log_seq_positive")),
        sa.CheckConstraint(f"hash ~ '{HEX64}'", name=op.f("ck_audit_log_hash_hex")),
        sa.CheckConstraint(f"prev_hash ~ '{HEX64}'", name=op.f("ck_audit_log_prev_hash_hex")),
        sa.CheckConstraint("jsonb_typeof(diff) = 'object'", name=op.f("ck_audit_log_diff_object")),
        sa.CheckConstraint(
            "jsonb_typeof(context) = 'object'", name=op.f("ck_audit_log_context_object")
        ),
    )
    # (company_id, seq) is indexed by the unique constraint above.
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_log_occurred_at", "audit_log", ["occurred_at"])

    op.create_table(
        "audit_chain_heads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seq", sa.BigInteger(), nullable=False),
        sa.Column("last_hash", sa.CHAR(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_chain_heads")),
        sa.UniqueConstraint(
            "company_id",
            name=op.f("uq_audit_chain_heads_company_id"),
            postgresql_nulls_not_distinct=True,
        ),
        sa.CheckConstraint("last_seq >= 0", name=op.f("ck_audit_chain_heads_last_seq_non_negative")),
        sa.CheckConstraint(
            f"last_hash ~ '{HEX64}'", name=op.f("ck_audit_chain_heads_last_hash_hex")
        ),
    )

    _execute_all(AUDIT_FUNCTIONS)
    _execute_all(AUDIT_TRIGGERS)
    _execute_all(AUDIT_RLS)
    _execute_all(AUDIT_GRANTS)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text("SELECT tableowner FROM pg_tables WHERE schemaname = 'public' AND tablename = 'audit_log'")
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the audit core must run as the table owner ({owner}), not {current}"
        )
    allow_loss = context.get_x_argument(as_dictionary=True).get("allow_audit_data_loss") == "yes"
    has_entries = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM audit_log)")).scalar_one()
    if has_entries and not allow_loss:
        raise RuntimeError(
            "audit_log is not empty: dropping it destroys audit evidence. Export the log "
            "first and re-run with `-x allow_audit_data_loss=yes` if this is intended."
        )

    # DROP TABLE removes the triggers and policies attached to the tables.
    op.drop_table("audit_chain_heads")
    op.drop_index("ix_audit_log_occurred_at", table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.execute("DROP FUNCTION audit_chain_heads_check()")
    op.execute("DROP FUNCTION audit_log_check_append()")
    op.execute("DROP FUNCTION audit_log_reject_modification()")
    op.execute("DROP FUNCTION app_global_audit_read()")
    op.execute("DROP FUNCTION app_company_ids()")
    # alembic_version privileges are intentionally NOT restored: app_rw must never
    # write the migration state.
