"""Verified identity carried by a bearer token, and the verifier interface.

Two implementations, selected by ``AUTH_MODE`` in :func:`app.auth.verifier.build_verifier`
(ADR 0018):

- :class:`app.auth.local.LocalTokenVerifier` - access tokens of local accounts, issued by
  ``POST /auth/login`` / ``/auth/refresh`` (HS256, ``AUTH_JWT_SECRET``), bound to a
  server-side session (``sid``);
- :class:`app.auth.dev.DevTokenVerifier` - HS256 tokens issued by ``/auth/dev/token``.

Each verifier accepts exactly one algorithm, issuer and key (no confusion between modes).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

# Clock skew tolerated for exp / nbf / iat (seconds).
LEEWAY_SECONDS = 60


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired, or not issued for this API (-> 401)."""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: str  # users.external_id
    issuer: str
    email: str
    display_name: str
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @property
    def session_id(self) -> str | None:
        """``sid`` of a local access token (the server-side session), else ``None``."""
        value = self.raw.get("sid")
        return value if isinstance(value, str) and value else None


class TokenVerifier(Protocol):
    # True: every token belongs to a server-side session that is checked on each request
    # (local accounts); the login event is written by POST /auth/login, not on first use.
    session_bound: bool

    async def verify(self, token: str) -> TokenClaims: ...

    async def aclose(self) -> None: ...


def claims_from_payload(payload: Mapping[str, Any]) -> TokenClaims:
    """Map the standard claims (``sub`` required; ``email`` / ``name`` optional)."""
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise InvalidTokenError("token has no subject")

    def first_text(*names: str) -> str:
        for name in names:
            value = payload.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    email = first_text("email")
    return TokenClaims(
        subject=subject,
        issuer=str(payload.get("iss", "")),
        email=email,
        display_name=first_text("name") or email or subject,
        raw=dict(payload),
    )
