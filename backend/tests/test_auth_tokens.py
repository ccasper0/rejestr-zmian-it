"""Token verification: local accounts and dev (both HS256, separate keys/issuers). No I/O."""

from __future__ import annotations

import base64
import json
import time
from uuid import uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.auth.dev import DEV_AUDIENCE, DEV_ISSUER, DevTokenVerifier, issue_dev_token
from app.auth.local import LOCAL_AUDIENCE, LOCAL_ISSUER, LocalTokenVerifier, issue_access_token
from app.auth.tokens import InvalidTokenError
from app.auth.verifier import build_verifier
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import DEV_SECRET, make_settings


def _b64(value: object) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# --------------------------------------------------------------------------- settings


def test_dev_mode_requires_secret() -> None:
    with pytest.raises(ValidationError, match="DEV_AUTH_SECRET"):
        make_settings(dev_auth_secret=None)


def test_dev_secret_must_have_32_chars() -> None:
    with pytest.raises(ValidationError, match="DEV_AUTH_SECRET"):
        make_settings(dev_auth_secret="x" * 31)
    assert make_settings(dev_auth_secret="x" * 32).dev_auth_secret is not None


def test_local_mode_does_not_need_dev_secret() -> None:
    settings = make_settings(auth_mode="local", dev_auth_secret=None, auth_jwt_secret=LOCAL_SECRET)
    assert settings.auth_mode == "local"
    assert isinstance(build_verifier(settings), LocalTokenVerifier)


def test_dev_secret_is_not_leaked_in_repr() -> None:
    assert DEV_SECRET not in repr(make_settings())


# --------------------------------------------------------------------------- dev tokens


def test_dev_token_round_trip() -> None:
    verifier = DevTokenVerifier(DEV_SECRET)
    token, expires_in = issue_dev_token(DEV_SECRET, "dev-editor")
    claims = verifier.verify_sync(token)
    assert claims.subject == "dev-editor"
    assert claims.issuer == DEV_ISSUER
    assert expires_in > 0
    assert verifier.session_bound is False


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(lambda p: p | {"exp": int(time.time()) - 3600}, id="expired"),
        pytest.param(lambda p: p | {"aud": "other"}, id="audience"),
        pytest.param(lambda p: p | {"iss": "other"}, id="issuer"),
        pytest.param(lambda p: {k: v for k, v in p.items() if k != "sub"}, id="no-sub"),
        pytest.param(lambda p: p | {"nbf": int(time.time()) + 3600}, id="not-yet-valid"),
    ],
)
def test_dev_token_claims_are_enforced(mutate: object) -> None:
    now = int(time.time())
    payload = {"iss": DEV_ISSUER, "aud": DEV_AUDIENCE, "sub": "x", "iat": now, "exp": now + 60}
    token = jwt.encode(mutate(payload), DEV_SECRET, algorithm="HS256")  # type: ignore[operator]
    with pytest.raises(InvalidTokenError):
        DevTokenVerifier(DEV_SECRET).verify_sync(token)


def test_dev_token_with_other_secret_rejected() -> None:
    token, _ = issue_dev_token("y" * 40, "dev-editor")
    with pytest.raises(InvalidTokenError):
        DevTokenVerifier(DEV_SECRET).verify_sync(token)


def test_dev_verifier_rejects_unsigned_and_rs256_tokens() -> None:
    now = int(time.time())
    payload = {"iss": DEV_ISSUER, "aud": DEV_AUDIENCE, "sub": "x", "iat": now, "exp": now + 60}
    unsigned = jwt.encode(payload, None, algorithm="none")
    hs512 = jwt.encode(payload, DEV_SECRET, algorithm="HS512")
    # A token claiming RS256 (algorithm confusion): forged header, arbitrary signature.
    rs256 = ".".join([_b64({"alg": "RS256", "typ": "JWT"}), _b64(payload), "c2lnbmF0dXJl"])
    for token in (unsigned, hs512, rs256, "not-a-jwt", ""):
        with pytest.raises(InvalidTokenError):
            DevTokenVerifier(DEV_SECRET).verify_sync(token)


# --------------------------------------------------------------------------- local tokens


def _local_payload(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    payload: dict[str, object] = {
        "iss": LOCAL_ISSUER,
        "aud": LOCAL_AUDIENCE,
        "sub": "local:abc",
        "sid": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + 600,
        "jti": "j1",
    }
    payload.update(overrides)
    return {k: v for k, v in payload.items() if v is not None}


def test_local_token_round_trip() -> None:
    sid = uuid4()
    token, expires_in = issue_access_token(
        LOCAL_SECRET, external_id="local:abc", session_id=sid, ttl_seconds=900
    )
    verifier = LocalTokenVerifier(LOCAL_SECRET)
    claims = verifier.verify_sync(token)
    assert claims.subject == "local:abc"
    assert claims.session_id == str(sid)
    assert expires_in == 900
    assert verifier.session_bound is True
    decoded = jwt.decode(token, options={"verify_signature": False})
    # No secrets, no roles in the token.
    assert set(decoded) == {"iss", "aud", "sub", "sid", "iat", "nbf", "exp", "jti"}


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"exp": int(time.time()) - 3600}, id="expired"),
        pytest.param({"aud": "other"}, id="audience"),
        pytest.param({"iss": DEV_ISSUER}, id="dev-issuer"),
        pytest.param({"sid": None}, id="no-sid"),
        pytest.param({"sid": "not-a-uuid"}, id="bad-sid"),
        pytest.param({"jti": None}, id="no-jti"),
        pytest.param({"sub": None}, id="no-sub"),
    ],
)
def test_local_token_claims_are_enforced(overrides: dict[str, object]) -> None:
    token = jwt.encode(_local_payload(**overrides), LOCAL_SECRET, algorithm="HS256")
    with pytest.raises(InvalidTokenError):
        LocalTokenVerifier(LOCAL_SECRET).verify_sync(token)


def test_dev_and_local_tokens_are_not_interchangeable() -> None:
    dev_token, _ = issue_dev_token(DEV_SECRET, "dev-editor")
    with pytest.raises(InvalidTokenError):
        LocalTokenVerifier(DEV_SECRET).verify_sync(dev_token)
    local_token, _ = issue_access_token(
        LOCAL_SECRET, external_id="x", session_id=uuid4(), ttl_seconds=60
    )
    with pytest.raises(InvalidTokenError):
        DevTokenVerifier(LOCAL_SECRET).verify_sync(local_token)


def test_local_verifier_rejects_other_algorithms_and_keys() -> None:
    payload = _local_payload()
    for token in (
        jwt.encode(payload, None, algorithm="none"),
        jwt.encode(payload, LOCAL_SECRET, algorithm="HS512"),
        jwt.encode(payload, "z" * 64, algorithm="HS256"),
    ):
        with pytest.raises(InvalidTokenError):
            LocalTokenVerifier(LOCAL_SECRET).verify_sync(token)


async def test_unconfigured_local_verifier_rejects_everything() -> None:
    token = jwt.encode(_local_payload(), LOCAL_SECRET, algorithm="HS256")
    verifier = LocalTokenVerifier(None)
    with pytest.raises(InvalidTokenError, match="not configured"):
        await verifier.verify(token)
    await verifier.aclose()
