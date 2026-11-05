"""Local accounts (``AUTH_MODE=local`` only — the router is not mounted otherwise, ADR 0018).

- ``POST /auth/login`` (public): e-mail + password -> access token + refresh token;
- ``POST /auth/refresh`` (public): refresh token -> new pair (rotation, reuse detection);
- ``POST /auth/logout`` (self): ends the session of the access token;
- ``POST /auth/password`` (self): change of the own password (current + new) - every
  session ends, a new pair is returned.

``logout`` and ``password`` are allowed also while a temporary password must be changed.
Token responses carry ``Cache-Control: no-store`` (RFC 6749 §5.1).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select

from app.auth.dependencies import PendingPasswordUserDep
from app.auth.local import issue_access_token
from app.auth.passwords import hash_password_async, verify_password_async
from app.config import Settings
from app.db import SessionDep, get_database
from app.domain.passwords import MESSAGES, check_password
from app.errors import ProblemError
from app.models import User
from app.schemas.identity import LoginIn, PasswordChangeIn, RefreshIn, SessionTokensOut
from app.services import local_auth

router = APIRouter(prefix="/auth", tags=["auth"])

NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _policy(request: Request) -> local_auth.AuthPolicy:
    return local_auth.AuthPolicy.from_settings(_settings(request))


def _request_info(request: Request) -> local_auth.RequestInfo:
    return local_auth.RequestInfo(method=request.method, path=request.url.path)


def _tokens(
    request: Request, response: Response, issued: local_auth.IssuedSession
) -> SessionTokensOut:
    settings = _settings(request)
    secret = settings.auth_jwt_secret
    if secret is None:  # pragma: no cover - Settings requires it in local mode
        raise RuntimeError("AUTH_JWT_SECRET is not set")
    access, expires_in = issue_access_token(
        secret.get_secret_value(),
        external_id=issued.user.external_id,
        session_id=issued.session_id,
        ttl_seconds=settings.auth_access_token_minutes * 60,
    )
    response.headers.update(NO_STORE)
    now = datetime.now(UTC)
    return SessionTokensOut(
        access_token=access,
        expires_in=expires_in,
        refresh_token=issued.refresh_token,
        refresh_expires_in=max(0, int((issued.refresh_expires_at - now).total_seconds())),
        session_expires_at=issued.session_expires_at,
        must_change_password=issued.must_change_password,
    )


def invalid_credentials() -> ProblemError:
    # One answer for every failure (unknown e-mail, wrong password, locked or inactive
    # account, no password): nothing reveals whether the account exists (ADR 0018 §3).
    return ProblemError(
        status=401,
        code="auth.invalid_credentials",
        detail="Nieprawidłowy e-mail lub hasło. Jeśli problem się powtarza, konto może być "
        "czasowo zablokowane lub nieaktywne - skontaktuj się z administratorem.",
        headers=NO_STORE,
    )


def temporary_password_expired() -> ProblemError:
    # Only after the RIGHT password (or a valid refresh token of the session): it tells
    # nothing to someone who does not know the password (ADR 0018 §12 p. 4).
    return ProblemError(
        status=401,
        code="auth.temporary_password_expired",
        detail="Hasło tymczasowe wygasło. Poproś administratora o ponowne ustawienie hasła.",
        headers=NO_STORE,
    )


@router.post("/login", response_model=SessionTokensOut)
async def login(body: LoginIn, request: Request, response: Response) -> SessionTokensOut:
    result = await local_auth.login(
        get_database(request),
        email=body.email,
        password=body.password,
        policy=_policy(request),
        request=_request_info(request),
    )
    if result.failure is local_auth.AuthFailure.RATE_LIMITED:
        raise ProblemError(
            status=429,
            code="auth.too_many_attempts",
            detail="Zbyt wiele nieudanych prób logowania z tej sieci. Spróbuj ponownie później.",
            headers={**NO_STORE, "Retry-After": str(result.retry_after or 60)},
        )
    if result.failure is local_auth.AuthFailure.TEMPORARY_PASSWORD_EXPIRED:
        raise temporary_password_expired()
    if result.issued is None:
        raise invalid_credentials()
    return _tokens(request, response, result.issued)


@router.post("/refresh", response_model=SessionTokensOut)
async def refresh(body: RefreshIn, request: Request, response: Response) -> SessionTokensOut:
    result = await local_auth.refresh(
        get_database(request),
        refresh_token=body.refresh_token,
        policy=_policy(request),
        request=_request_info(request),
    )
    if result.failure is local_auth.AuthFailure.TEMPORARY_PASSWORD_EXPIRED:
        raise temporary_password_expired()
    if result.issued is None:
        raise ProblemError(
            status=401,
            code="auth.invalid_refresh_token",
            detail="Sesja wygasła lub została zakończona. Zaloguj się ponownie.",
            headers=NO_STORE,
        )
    return _tokens(request, response, result.issued)


@router.post("/logout", status_code=204)
async def logout(user: PendingPasswordUserDep, session: SessionDep) -> Response:
    if user.session_id is None:  # pragma: no cover - local tokens always carry a session
        raise ProblemError(
            status=400, code="auth.no_session", detail="Token nie jest powiązany z sesją."
        )
    await local_auth.logout(
        session, actor=user.actor(), user_id=user.id, session_id=user.session_id
    )
    return Response(status_code=204, headers=NO_STORE)


@router.post("/password", response_model=SessionTokensOut)
async def change_password(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    user: PendingPasswordUserDep,
    session: SessionDep,
) -> SessionTokensOut:
    db_user = await session.get(User, user.id)
    credential = await local_auth.get_credential(session, user.id)
    if db_user is None or credential is None:
        raise ProblemError(
            status=409,
            code="auth.password_not_set",
            detail="To konto nie ma hasła. Poproś administratora o reset hasła.",
        )
    now = (await session.execute(select(func.clock_timestamp()))).scalar_one()
    if credential.locked_until is not None and credential.locked_until > now:
        raise ProblemError(
            status=423,
            code="auth.account_locked",
            detail="Konto jest czasowo zablokowane po nieudanych próbach. Spróbuj później "
            "albo poproś administratora o reset hasła.",
        )
    policy = _policy(request)
    if not await verify_password_async(credential.password_hash, body.current_password):
        await local_auth.record_wrong_current_password(
            get_database(request),
            session,
            user=db_user,
            actor=user.actor(),
            policy=policy,
            request=_request_info(request),
        )
        raise ProblemError(
            status=400,
            code="auth.invalid_current_password",
            detail="Obecne hasło jest nieprawidłowe.",
        )
    check = check_password(
        body.new_password, email=db_user.email, display_name=db_user.display_name
    )
    if check.problem is not None:
        raise ProblemError(status=422, code=check.problem.value, detail=MESSAGES[check.problem])
    if await verify_password_async(credential.password_hash, body.new_password):
        raise ProblemError(
            status=422,
            code="auth.password_reused",
            detail="Nowe hasło musi się różnić od obecnego.",
        )
    new_hash = await hash_password_async(body.new_password)
    issued = await local_auth.change_password(
        session, user=db_user, actor=user.actor(), new_password_hash=new_hash, policy=policy
    )
    return _tokens(request, response, issued)
