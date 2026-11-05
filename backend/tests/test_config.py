import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.main import create_app
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import make_settings

ENV_VARS = (
    "APP_ENV",
    "AUTH_MODE",
    "CORS_ORIGINS",
    "LOG_LEVEL",
    "DATABASE_URL",
    "MIGRATIONS_DATABASE_URL",
    "REDIS_URL",
    "STORAGE_PATH",
    "DEV_AUTH_SECRET",
    "AUTH_JWT_SECRET",
    "AUTH_ACCESS_TOKEN_MINUTES",
    "AUTH_REFRESH_IDLE_MINUTES",
    "TEMP_PASSWORD_TTL_HOURS",
    "AUTH_SESSION_MAX_HOURS",
    "AUTH_LOCKOUT_THRESHOLD",
    "AUTH_LOCKOUT_MINUTES",
    "AUTH_LOGIN_MAX_FAILURES_PER_NETWORK",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_defaults_are_safe() -> None:
    s = Settings(_env_file=None)
    assert s.auth_mode == "local"
    assert s.app_env == "prod"
    assert s.cors_origins == []


def test_prod_with_dev_auth_is_refused() -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE=dev"):
        make_settings(app_env="prod", auth_mode="dev")


def test_prod_with_dev_auth_refused_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "dev")
    with pytest.raises(ValidationError, match="AUTH_MODE=dev"):
        Settings(_env_file=None)


def test_app_factory_refuses_to_start_in_prod_with_dev_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "dev")
    get_settings.cache_clear()
    try:
        with pytest.raises(ValidationError, match="AUTH_MODE=dev"):
            create_app()
    finally:
        get_settings.cache_clear()


def test_prod_with_local_auth_is_allowed() -> None:
    s = make_settings(app_env="prod", auth_mode="local", auth_jwt_secret=LOCAL_SECRET)
    assert s.app_env == "prod"
    assert s.missing_auth_settings() == []
    assert LOCAL_SECRET not in repr(s)


def test_local_auth_without_secret_is_reported_for_startup() -> None:
    s = make_settings(auth_mode="local")
    assert s.missing_auth_settings() == ["AUTH_JWT_SECRET"]
    assert make_settings().missing_auth_settings() == []  # dev mode


@pytest.mark.parametrize(
    ("app_env", "secret"),
    [
        ("prod", "a1b2c3d4e5f6g7h8" * 3),  # 48 chars: enough for dev, not for prod
        ("dev", "a1b2c3d4e5f6g7h"),  # 15 chars
        ("dev", "x" * 40),  # not random
    ],
)
def test_weak_jwt_secret_is_refused(app_env: str, secret: str) -> None:
    with pytest.raises(ValidationError, match="AUTH_JWT_SECRET"):
        make_settings(app_env=app_env, auth_mode="local", auth_jwt_secret=secret)


def test_jwt_secret_length_depends_on_environment() -> None:
    secret = "a1b2c3d4e5f6g7h8" * 3
    assert make_settings(app_env="dev", auth_mode="local", auth_jwt_secret=secret)


def test_cors_origins_parsed_from_comma_separated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000, http://127.0.0.1:8080 ,")
    s = Settings(_env_file=None)
    assert s.cors_origins == ["http://localhost:5000", "http://127.0.0.1:8080"]


def test_invalid_auth_mode_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(auth_mode="none")


def test_env_variables_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app_rw:pw@db:5432/rejestr")
    monkeypatch.setenv("MIGRATIONS_DATABASE_URL", "postgresql+asyncpg://app_owner:pw@db:5432/r")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("STORAGE_PATH", "/data/storage")
    s = Settings(_env_file=None)
    assert s.database_url == "postgresql+asyncpg://app_rw:pw@db:5432/rejestr"
    assert s.migrations_database_url.startswith("postgresql+asyncpg://app_owner")
    assert s.redis_url == "redis://redis:6379/0"
    assert s.log_level == "DEBUG"
    assert str(s.storage_path).replace("\\", "/").endswith("data/storage")


def test_temporary_password_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    # ADR 0018 §12 p. 4: a temporary password is valid for 7 days unless configured.
    assert Settings(_env_file=None).temp_password_ttl_hours == 168
    monkeypatch.setenv("TEMP_PASSWORD_TTL_HOURS", "24")
    assert Settings(_env_file=None).temp_password_ttl_hours == 24
    for invalid in (0, 24 * 31):
        with pytest.raises(ValidationError):
            make_settings(temp_password_ttl_hours=invalid)
