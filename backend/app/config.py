"""Application configuration (pydantic-settings).

Every variable is documented in the repository-level ``.env.example``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.services.file_types import DEFAULT_ALLOWED_TYPES, parse_allowed_types

AppEnv = Literal["dev", "prod"]
AuthMode = Literal["local", "dev"]
LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
LogFormat = Literal["json", "console"]

DEV_AUTH_SECRET_MIN_LENGTH = 32
# AUTH_JWT_SECRET (AUTH_MODE=local, ADR 0018): HS256 key of the access tokens. The key
# must carry at least 256 bits; in production a longer random value is required.
AUTH_JWT_SECRET_MIN_LENGTH = 32
AUTH_JWT_SECRET_MIN_LENGTH_PROD = 64


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Safe by default: unless explicitly told otherwise we behave as production.
    app_env: AppEnv = "prod"
    auth_mode: AuthMode = "local"

    # Runtime connection (role app_rw — INSERT/SELECT only on audit tables, see CLAUDE.md 6.3).
    database_url: str = "postgresql+asyncpg://app_rw@localhost:5432/rejestr"
    # Migrations only (role app_owner). Never used by the running API.
    migrations_database_url: str = "postgresql+asyncpg://app_owner@localhost:5432/rejestr"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    log_level: LogLevel = "INFO"
    # Application logs (api, worker): one JSON object per line (production, log shipping)
    # or human-readable lines (local console). ADR 0019 §4.
    log_format: LogFormat = "json"
    storage_path: Path = Path("./storage")
    # Upper limit of one attachment (bytes); larger uploads get 413 (ADR 0013 §4).
    attachment_max_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    # Whitelist of attachment types, detected from the file content (ADR 0019 §3);
    # anything else gets 415 attachment.type_not_allowed.
    attachment_allowed_types: Annotated[frozenset[str], NoDecode] = Field(
        default_factory=lambda: frozenset(DEFAULT_ALLOWED_TYPES)
    )
    # "Łańcuch spójny" badge (GET /companies/{id}/audit/status): the last recorded
    # verification older than this is reported as "stale" (ADR 0013 §11). The worker
    # verifies every chain daily.
    audit_status_max_age_hours: int = Field(default=26, ge=1)
    # Reports (CLAUDE.md §9, ADR 0017): a register report with MORE changes than this is
    # generated in the background by the worker (POST /reports -> 202, status pending);
    # smaller ones (and every change card) synchronously in the request.
    report_async_threshold: int = Field(default=200, ge=0)
    # Upper limit of changes in one register report / CSV export (422 report.too_large).
    report_max_changes: int = Field(default=5000, ge=1)

    # Max time the health check waits for "SELECT 1".
    db_health_timeout_seconds: float = Field(default=2.0, gt=0)

    # Connection pools per process (app.db.Database, ADR 0010 §5): the main pool for request
    # transactions and a separate auxiliary pool for the short authentication/audit-event
    # transactions, so that they can never wait for a connection of the main pool.
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout_seconds: float = Field(default=30.0, gt=0)
    db_aux_pool_size: int = Field(default=2, ge=1)
    db_aux_max_overflow: int = Field(default=3, ge=0)

    # Local accounts with passwords (AUTH_MODE=local, ADR 0018). SecretStr: never printed.
    # Required with AUTH_MODE=local (checked when the API starts serving); min. 32
    # characters, 64 with APP_ENV=prod.
    auth_jwt_secret: SecretStr | None = None
    # Lifetime of an access token (minutes); the session is checked on every request, so
    # logout / password change / deactivation take effect at once anyway.
    auth_access_token_minutes: int = Field(default=15, ge=1, le=60)
    # A refresh token expires when unused for this long (idle timeout of the session).
    auth_refresh_idle_minutes: int = Field(default=120, ge=5, le=7 * 24 * 60)
    # Absolute lifetime of a session (from the login); afterwards log in again.
    auth_session_max_hours: int = Field(default=12, ge=1, le=7 * 24)
    # Account lockout: this many consecutive failed passwords lock the account for
    # auth_lockout_minutes (unlocked by time or by an admin password reset).
    auth_lockout_threshold: int = Field(default=5, ge=3, le=100)
    auth_lockout_minutes: int = Field(default=15, ge=1, le=24 * 60)
    # Login attempts rejected (429) from one client network (IPv4 /32, IPv6 /64) once it
    # has this many failed logins in the current failure window (auth_failure_window_
    # seconds): stops password spraying over many accounts, which the per-account
    # lockout does not see. 0 disables the limit.
    auth_login_max_failures_per_network: int = Field(default=30, ge=0)
    # Validity of a temporary password (POST /users, reset by the admin, create-admin
    # --generate-password) in hours; afterwards the login is refused (401
    # auth.temporary_password_expired) and the admin must reset the password. A session
    # opened with it ends at the deadline too. ADR 0018 §12 p. 4: 7 days.
    temp_password_ttl_hours: int = Field(default=168, ge=1, le=30 * 24)

    # HS256 key of dev tokens (AUTH_MODE=dev only). SecretStr: never printed in repr/logs.
    dev_auth_secret: SecretStr | None = None

    # Failed authentications (login_failed) are aggregated per time window and bucket
    # (reason + client network), ADR 0010: the 1st, 2nd, 4th, 8th, ... failure of a bucket
    # in a window is written to the audit log at once, the exact total as a summary after
    # the window closes. More distinct buckets than the limit in one window are folded
    # into one "overflow" bucket per reason.
    # At most auth_failure_max_immediate_entries immediate entries per window over all
    # buckets; beyond it failures only appear in the window summaries (nothing is lost).
    auth_failure_window_seconds: int = Field(default=300, ge=10, le=86400)
    auth_failure_max_buckets: int = Field(default=200, ge=1)
    auth_failure_max_immediate_entries: int = Field(default=200, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    @field_validator("attachment_allowed_types", mode="before")
    @classmethod
    def _parse_allowed_types(cls, value: Any) -> Any:
        if isinstance(value, str):
            if not value.replace(",", "").strip():
                # Unset / empty variable (docker compose passes "") = the default list.
                return frozenset(DEFAULT_ALLOWED_TYPES)
            return parse_allowed_types(value.split(","))
        if isinstance(value, list | tuple | set | frozenset):
            return parse_allowed_types([str(item) for item in value])
        return value

    @field_validator("log_format", mode="before")
    @classmethod
    def _lower_log_format(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _forbid_dev_auth_in_prod(self) -> Self:
        if self.app_env == "prod" and self.auth_mode == "dev":
            raise ValueError(
                "AUTH_MODE=dev is forbidden when APP_ENV=prod "
                "(dev authentication must never be active in production)"
            )
        return self

    @model_validator(mode="after")
    def _dev_auth_needs_secret(self) -> Self:
        if self.auth_mode == "dev":
            secret = self.dev_auth_secret.get_secret_value() if self.dev_auth_secret else ""
            if len(secret) < DEV_AUTH_SECRET_MIN_LENGTH:
                raise ValueError(
                    f"DEV_AUTH_SECRET must be set to at least {DEV_AUTH_SECRET_MIN_LENGTH} "
                    "characters when AUTH_MODE=dev"
                )
        return self

    @model_validator(mode="after")
    def _local_auth_secret_strength(self) -> Self:
        # A MISSING secret is reported when the API starts serving (lifespan,
        # missing_auth_settings): importing app.main must not require it (tests, tools).
        # A secret that is set must be strong enough.
        if self.auth_mode == "local" and self.auth_jwt_secret is not None:
            secret = self.auth_jwt_secret.get_secret_value()
            minimum = (
                AUTH_JWT_SECRET_MIN_LENGTH_PROD
                if self.app_env == "prod"
                else AUTH_JWT_SECRET_MIN_LENGTH
            )
            if len(secret) < minimum:
                raise ValueError(
                    f"AUTH_JWT_SECRET must be set to at least {minimum} characters when "
                    f"AUTH_MODE=local and APP_ENV={self.app_env}"
                )
            if len(set(secret)) < 8:
                raise ValueError("AUTH_JWT_SECRET must be a random value (too few characters)")
        return self

    def missing_auth_settings(self) -> list[str]:
        """Names of variables required by AUTH_MODE=local that are empty."""
        if self.auth_mode != "local":
            return []
        secret = self.auth_jwt_secret.get_secret_value() if self.auth_jwt_secret else ""
        return [] if secret else ["AUTH_JWT_SECRET"]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
