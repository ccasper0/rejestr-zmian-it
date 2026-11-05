"""``current_user``: bearer token -> user (+ session) -> memberships -> RLS scope.

Two transactions per authenticated request (ADR 0007 §2-3):

1. a short one of its own (``run_in_separate_transaction``), COMMITTED first: user lookup,
   the session check of a local account (revoked / expired, ``must_change_password``,
   ADR 0018) and, in dev mode, the ``login`` event (first request with a token, ADR 0010
   §1), which writes to the GLOBAL audit chain. Keeping it in the request transaction
   would hold the global chain head until COMMIT, before the endpoint locks company
   rows/chains — the reverse of ADR 0006 §7 (deadlock);
2. the request's business transaction (``SessionDep``): ``app.user_id``, memberships and
   the company scope (RLS) are set in it; the endpoint receives this very session.

Failed authentications (``login_failed``) are recorded by ``app.auth.events`` in their own
transaction too, before the 401/403 is raised.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.events import FailureReason, record_access_denied, record_login_failed
from app.auth.principal import CurrentUser
from app.auth.tokens import InvalidTokenError, TokenVerifier
from app.db import (
    SessionDep,
    apply_company_scope,
    get_database,
    run_in_separate_transaction,
    set_current_user,
)
from app.errors import ProblemError
from app.logs import bind as bind_log_fields
from app.models import User
from app.services import auth_events, local_auth
from app.services import memberships as memberships_service
from app.services import users as users_service

_bearer = HTTPBearer(auto_error=False, description="Token dostępu JWT (konto lokalne lub dev)")


def invalid_token() -> ProblemError:
    return ProblemError(
        status=401,
        code="auth.invalid_token",
        detail="Brak ważnego tokenu uwierzytelniającego. Zaloguj się ponownie.",
        headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
    )


def get_token_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier = request.app.state.token_verifier
    return verifier


async def _authenticate(
    request: Request,
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials | None,
    verifier: TokenVerifier,
    *,
    password_change_pending_ok: bool,
) -> CurrentUser:
    if credentials is None or not credentials.credentials.strip():
        await record_login_failed(request, session, reason=FailureReason.MISSING_TOKEN)
        raise invalid_token()
    try:
        claims = await verifier.verify(credentials.credentials)
    except InvalidTokenError as exc:
        await record_login_failed(
            request, session, reason=FailureReason.INVALID_TOKEN, detail=str(exc)
        )
        raise invalid_token() from exc

    async def identify(
        identity_session: AsyncSession,
    ) -> tuple[User | None, local_auth.SessionState | None]:
        user = await users_service.resolve_identity(identity_session, claims)
        if user is None or not user.is_active:
            return user, None
        if verifier.session_bound:
            # Local account: the session must be live (logout, password change/reset,
            # deactivation revoke it at once, ADR 0018 §4). The login entry was written
            # by POST /auth/login.
            sid = claims.session_id
            state = (
                None
                if sid is None
                else await local_auth.check_session(
                    identity_session, user_id=user.id, session_id=UUID(sid)
                )
            )
            return user, state
        # Dev token: first request with this token = "login" (ADR 0010 §1).
        await auth_events.register_login(identity_session, user=user, claims=claims)
        return user, None

    # Before the request session executes anything: it holds no lock and no connection.
    user, state = await run_in_separate_transaction(get_database(request), identify, outer=session)
    if user is None:
        await record_login_failed(
            request, session, reason=FailureReason.UNKNOWN_USER, subject=claims.subject
        )
        raise invalid_token()
    # Every authenticated route - also /me and /auth/* without a permission declaration
    # (app.permissions binds only there) - has the user in its log lines (ADR 0019 §4).
    bind_log_fields(user_id=user.id)

    if not user.is_active:
        await record_login_failed(
            request,
            session,
            reason=FailureReason.USER_INACTIVE,
            actor=auth_events.actor_for_user(user),
        )
        raise ProblemError(
            status=403,
            code="auth.user_inactive",
            detail="Konto użytkownika jest nieaktywne. Skontaktuj się z administratorem.",
        )

    if verifier.session_bound and state is None:
        await record_login_failed(
            request,
            session,
            reason=FailureReason.SESSION_INVALID,
            actor=auth_events.actor_for_user(user),
        )
        raise ProblemError(
            status=401,
            code="auth.session_expired",
            detail="Sesja wygasła lub została zakończona. Zaloguj się ponownie.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    await set_current_user(session, user.id)
    roles = await memberships_service.roles_by_company(session, user.id)
    principal = CurrentUser(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        display_name=user.display_name,
        is_app_admin=user.is_app_admin,
        memberships=roles,
        session_id=UUID(claims.session_id) if claims.session_id else None,
        must_change_password=bool(state and state.must_change_password),
    )
    if principal.must_change_password and not password_change_pending_ok:
        await record_access_denied(
            request, session, user=principal, status=403, reason="password_change_required"
        )
        raise ProblemError(
            status=403,
            code="auth.password_change_required",
            detail="Przed dalszą pracą musisz zmienić hasło tymczasowe.",
        )
    await apply_company_scope(
        session, principal.company_ids, global_audit_read=principal.global_audit_read
    )
    return principal


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> CurrentUser:
    """The authenticated user; 403 ``auth.password_change_required`` while a temporary
    password has not been changed (ADR 0018 §5)."""
    return await _authenticate(
        request, session, credentials, verifier, password_change_pending_ok=False
    )


async def get_current_user_pending_password_change(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> CurrentUser:
    """Like :func:`get_current_user`, but also while the password must be changed - ONLY
    for ``GET /me``, ``POST /auth/password`` and ``POST /auth/logout`` (ADR 0018 §5)."""
    return await _authenticate(
        request, session, credentials, verifier, password_change_pending_ok=True
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
# Only the endpoints allowed with a temporary password (``/me``, ``/auth/password``,
# ``/auth/logout``); every other endpoint uses ``CurrentUserDep`` (directly or through
# ``app.permissions``).
PendingPasswordUserDep = Annotated[CurrentUser, Depends(get_current_user_pending_password_change)]
