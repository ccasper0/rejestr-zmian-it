"""Test secrets for the token keys (never real secrets)."""

from __future__ import annotations

# Dev-auth HS256 secret used by tests only.
DEV_SECRET = "test-dev-auth-secret-0123456789abcdef"

# AUTH_JWT_SECRET of local accounts in tests (64+ characters: valid also with APP_ENV=prod).
LOCAL_SECRET = "test-local-jwt-secret-0123456789abcdefghijklmnopqrstuvwxyzABCDEFGH"
