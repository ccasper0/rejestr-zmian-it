"""Select the token verifier for ``AUTH_MODE`` (``local`` | ``dev``, ADR 0018)."""

from __future__ import annotations

from app.auth.dev import DevTokenVerifier
from app.auth.local import LocalTokenVerifier
from app.auth.tokens import TokenVerifier
from app.config import Settings


def build_verifier(settings: Settings) -> TokenVerifier:
    if settings.auth_mode == "dev":
        if settings.dev_auth_secret is None:  # pragma: no cover - Settings validates it
            raise RuntimeError("DEV_AUTH_SECRET is required when AUTH_MODE=dev")
        return DevTokenVerifier(settings.dev_auth_secret.get_secret_value())
    # Without AUTH_JWT_SECRET the API refuses to serve (lifespan); the verifier built here
    # (import, tools) then rejects every token.
    secret = settings.auth_jwt_secret.get_secret_value() if settings.auth_jwt_secret else None
    return LocalTokenVerifier(secret)
