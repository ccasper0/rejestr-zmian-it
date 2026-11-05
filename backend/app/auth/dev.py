"""Dev authentication (``AUTH_MODE=dev``): HS256 tokens signed with ``DEV_AUTH_SECRET``.

Never active in production: ``Settings`` refuses ``AUTH_MODE=dev`` with ``APP_ENV=prod``,
and the ``/auth/dev/*`` routes are only mounted in dev mode.
"""

from __future__ import annotations

import time

import jwt

from app.auth.tokens import LEEWAY_SECONDS, InvalidTokenError, TokenClaims, claims_from_payload

DEV_ISSUER = "urn:rejestr:dev-auth"
DEV_AUDIENCE = "urn:rejestr:api"
DEV_ALGORITHM = "HS256"
DEV_TOKEN_TTL_SECONDS = 8 * 3600


def issue_dev_token(secret: str, external_id: str) -> tuple[str, int]:
    """Signed dev token for ``external_id``; returns ``(token, expires_in_seconds)``."""
    now = int(time.time())
    payload = {
        "iss": DEV_ISSUER,
        "aud": DEV_AUDIENCE,
        "sub": external_id,
        "iat": now,
        "nbf": now,
        "exp": now + DEV_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm=DEV_ALGORITHM), DEV_TOKEN_TTL_SECONDS


class DevTokenVerifier:
    # Stateless: the "login" is the first request with a token (ADR 0010 §1).
    session_bound = False

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def verify_sync(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[DEV_ALGORITHM],
                audience=DEV_AUDIENCE,
                issuer=DEV_ISSUER,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        return claims_from_payload(payload)

    async def verify(self, token: str) -> TokenClaims:
        return self.verify_sync(token)

    async def aclose(self) -> None:
        return None
