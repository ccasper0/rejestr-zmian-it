"""Access tokens of local accounts (``AUTH_MODE=local``, ADR 0018 §4).

HS256 JWT signed with ``AUTH_JWT_SECRET``: ``iss = urn:rejestr:local-auth``,
``aud = urn:rejestr:api``, ``sub = users.external_id``, ``sid`` = the server-side session
(``auth_sessions.id``), ``iat``/``nbf``/``exp`` (``AUTH_ACCESS_TOKEN_MINUTES``) and a random
``jti``. The token carries no roles and no secrets: roles are read from the database on
every request, and the session is checked on every request too (``revoked_at``,
``expires_at``), so logout, a password change/reset and deactivation end every session at
once - the short token lifetime only bounds the damage of a leaked token when the session
check could not run.
"""

from __future__ import annotations

import secrets
import time
from uuid import UUID

import jwt

from app.auth.tokens import LEEWAY_SECONDS, InvalidTokenError, TokenClaims, claims_from_payload

LOCAL_ISSUER = "urn:rejestr:local-auth"
LOCAL_AUDIENCE = "urn:rejestr:api"
LOCAL_ALGORITHM = "HS256"


def issue_access_token(
    secret: str, *, external_id: str, session_id: UUID, ttl_seconds: int
) -> tuple[str, int]:
    """Signed access token; returns ``(token, expires_in_seconds)``."""
    now = int(time.time())
    payload = {
        "iss": LOCAL_ISSUER,
        "aud": LOCAL_AUDIENCE,
        "sub": external_id,
        "sid": str(session_id),
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, secret, algorithm=LOCAL_ALGORITHM), ttl_seconds


class LocalTokenVerifier:
    session_bound = True

    def __init__(self, secret: str | None) -> None:
        self._secret = secret

    def verify_sync(self, token: str) -> TokenClaims:
        if not self._secret:
            raise InvalidTokenError("local authentication is not configured")
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[LOCAL_ALGORITHM],
                audience=LOCAL_AUDIENCE,
                issuer=LOCAL_ISSUER,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "nbf", "sub", "iss", "aud", "sid", "jti"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        sid = payload.get("sid")
        try:
            UUID(str(sid))
        except ValueError as exc:
            raise InvalidTokenError("token has an invalid session id") from exc
        return claims_from_payload(payload)

    async def verify(self, token: str) -> TokenClaims:
        return self.verify_sync(token)

    async def aclose(self) -> None:
        return None
