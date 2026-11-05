"""RBAC — the single source of truth (CLAUDE.md §5).

Every endpoint declares one ``Action`` through one of the dependencies below, or is listed
in ``PUBLIC_ENDPOINTS`` (no authentication) / ``SELF_ENDPOINTS`` (authenticated, returns
only the caller's own data). ``tests/test_rbac_matrix.py`` checks every route.

Conditional rules that depend on the resource (e.g. "approver cannot approve own change",
four-eyes principle) are enforced in ``app.domain.state_machine`` on top of this matrix.

Dependencies (each returns ``fastapi.Depends``):

- :func:`require` — global action (no company in the path): companies, dictionaries,
  users. Only ``app_admin`` is a global role. Opens the explicit admin scope.
- :func:`require_company` — ``get_company_context``: the company from the path must have a
  membership of the user (otherwise **404** ``company.not_found``, §7.3 — also for app
  admins: an admin is not implicitly a member, §5), then the action is checked on the
  user's roles in that company (plus ``app_admin``), otherwise 403. With ``admin_action``
  an app admin may instead use the explicit administrative path for this endpoint; that
  path skips the check of ``action``, so it is accepted only for ``READ_ACTIONS``, or when
  ``admin_action`` is ``action`` itself and ``app_admin`` holds it in the matrix (e.g. the
  CI inventory, §5) (:func:`_check_admin_action`, raised when the route is declared).
  With ``admin_read_only`` the admin path is the NARROW READ-ONLY path
  (:func:`_admin_read_context`), taken only by an admin WITHOUT a membership in the
  company; an admin with a role there is resolved by those roles like any member.
- :func:`require_register_read` — the named admin read path of the change register
  (list, card, readiness, change audit trail, attachment list, tiles): members by their
  roles, an app admin without a role read-only (owner decision 2026-11-02, ADR 0016).
- :func:`require_admin_company` — administrative action on one company (edit, archive,
  role assignment): global check (403) first, then the company (404 if it does not exist).
- :func:`visible_companies` — list endpoints: which companies the action is allowed in.
- :func:`require_in_any_company` — global READ of shared dictionaries (categories, CI
  types): allowed when the action is allowed in at least one company of the user (or
  globally, ``app_admin``); otherwise 403. No admin scope is opened (ADR 0011).
- :func:`require_audit_chain` — one audit chain chosen by the optional query parameter
  ``company_id`` (omitted = the global chain, app admins only; ADR 0009).
- :func:`require_change_action` — ``POST /companies/{company_id}/changes/{id}/actions/
  {action}``: membership (else 404), then the matrix action of the path's change action
  (:data:`CHANGE_ACTION_PERMISSIONS`, else 403). No admin path (ADR 0013 §7, ADR 0016).
- :func:`require_report_order`, :func:`require_report_list`, :func:`require_report` —
  report exports (``/reports``, ADR 0017): the company comes from the body / the query /
  the stored report; ``export.register`` or ``export.change_card`` by the report kind
  (:data:`REPORT_KIND_PERMISSIONS`); the app admin on the named admin export path.
- :func:`require_register_export` — the CSV export of the register: members by their
  roles, an app admin without a role on the named admin export path (ADR 0017 §14).

Every denial (403, and 404 for a company without membership) is recorded in the audit
log (``access_denied``, global chain) by ``app.auth.events`` before the request fails.
"""

# No ``from __future__ import annotations``: the dependency functions below are defined
# inside factories with locally imported types, and FastAPI resolves string annotations
# against module globals only. Annotations here are therefore evaluated eagerly.

import functools
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal
from uuid import UUID

from fastapi import Depends, Request

# Re-exported: defined in the domain (pure rules use them), the matrix below stays here.
from app.domain.roles import MEMBERSHIP_ROLES as MEMBERSHIP_ROLES
from app.domain.roles import Role as Role

if TYPE_CHECKING:
    from fastapi import FastAPI
    from fastapi.dependencies.models import Dependant
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.auth.principal import CompanyContext, CurrentUser


class Action(StrEnum):
    COMPANY_MANAGE = "company.manage"  # add, edit, archive companies
    DICTIONARY_MANAGE = "dictionary.manage"  # global categories, CI types
    MEMBERSHIP_MANAGE = "membership.manage"  # assign roles in a company
    USER_MANAGE = "user.manage"  # local accounts: create, reset password, (de)activate
    CI_MANAGE = "ci.manage"  # company CI inventory CRUD (deactivate, no delete)
    CHANGE_EDIT_DRAFT = "change.edit_draft"  # create / edit changes in draft
    CHANGE_ASSIGN = "change.assign"  # assign category, CI, assignee, approver
    CHANGE_APPROVE = "change.approve"  # approve / reject (not own — domain rule)
    REGISTER_VIEW = "register.view"  # register, change cards, audit trail
    EXPORT_REGISTER = "export.register"  # register PDF/CSV
    EXPORT_CHANGE_CARD = "export.change_card"  # single change card PDF
    AUDIT_VERIFY = "audit.verify"  # audit chain verification
    AUDIT_READ = "audit.read"  # browse the whole audit log (GET /audit), ADR 0009


_ALL = frozenset(Role)

PERMISSIONS: MappingProxyType[Action, frozenset[Role]] = MappingProxyType(
    {
        Action.COMPANY_MANAGE: frozenset({Role.APP_ADMIN}),
        Action.DICTIONARY_MANAGE: frozenset({Role.APP_ADMIN}),
        Action.MEMBERSHIP_MANAGE: frozenset({Role.APP_ADMIN}),
        Action.USER_MANAGE: frozenset({Role.APP_ADMIN}),
        Action.CI_MANAGE: frozenset({Role.APP_ADMIN, Role.APPROVER, Role.EDITOR}),
        Action.CHANGE_EDIT_DRAFT: frozenset({Role.APPROVER, Role.EDITOR}),
        Action.CHANGE_ASSIGN: frozenset({Role.APPROVER, Role.EDITOR}),
        Action.CHANGE_APPROVE: frozenset({Role.APPROVER}),
        Action.REGISTER_VIEW: _ALL,
        Action.EXPORT_REGISTER: frozenset({Role.APP_ADMIN, Role.APPROVER, Role.AUDITOR}),
        Action.EXPORT_CHANGE_CARD: frozenset(
            {Role.APP_ADMIN, Role.APPROVER, Role.EDITOR, Role.AUDITOR}
        ),
        Action.AUDIT_VERIFY: frozenset({Role.APP_ADMIN, Role.AUDITOR}),
        Action.AUDIT_READ: frozenset({Role.APP_ADMIN, Role.AUDITOR}),
    }
)

# Polish description of every matrix row (label, note) for the read-only matrix in the UI
# (``GET /permissions/matrix``, ADR 0015). Presentation only - who holds an action is
# decided by ``PERMISSIONS`` above; a test requires a description for every ``Action``.
ACTION_DESCRIPTIONS: MappingProxyType[Action, tuple[str, str | None]] = MappingProxyType(
    {
        Action.COMPANY_MANAGE: (
            "Zarządzanie spółkami (dodaj, edytuj, archiwizuj)",
            "Także kategorie dostępne w spółce. Spółek się nie usuwa.",
        ),
        Action.DICTIONARY_MANAGE: ("Słowniki globalne (kategorie, typy CI)", None),
        Action.MEMBERSHIP_MANAGE: (
            "Przypisywanie ról w spółce",
            "Nadanie roli samemu sobie też trafia do dziennika audytu.",
        ),
        Action.USER_MANAGE: (
            "Konta użytkowników (zakładanie, reset hasła, dezaktywacja)",
            "Hasło tymczasowe jest pokazywane tylko raz. Administrator nie dezaktywuje "
            "własnego konta ani ostatniego aktywnego administratora.",
        ),
        Action.CI_MANAGE: (
            "Inwentarz CI spółki (dodawanie, edycja)",
            "Bez usuwania — dezaktywacja.",
        ),
        Action.CHANGE_EDIT_DRAFT: (
            "Tworzenie i edycja zmian w szkicu",
            "Także wysłanie, wdrożenie, weryfikacja, wycofanie i anulowanie — zgodnie z "
            "rolą na zmianie (autor, wykonawca, weryfikujący).",
        ),
        Action.CHANGE_ASSIGN: (
            "Przypisywanie kategorii, CI, wykonawcy, zatwierdzającego",
            None,
        ),
        Action.CHANGE_APPROVE: (
            "Zatwierdzanie, odrzucanie, zwrot do poprawy",
            "Nie własnych zmian (zasada czterech oczu).",
        ),
        Action.REGISTER_VIEW: (
            "Podgląd rejestru, kart, ścieżki audytu zmiany",
            "Administrator bez roli w spółce — tylko odczyt: bez akcji, edycji, komentarzy "
            "i pobierania plików załączników (widzi ich listę z sha256).",
        ),
        Action.EXPORT_REGISTER: ("Eksport rejestru (PDF, CSV)", None),
        Action.EXPORT_CHANGE_CARD: ("Eksport karty zmiany (PDF)", None),
        Action.AUDIT_VERIFY: ("Weryfikacja łańcucha audytu", None),
        Action.AUDIT_READ: ("Przegląd całego dziennika audytu", None),
    }
)

# Routes without an Action. Public: technical, the login of local accounts (mounted only
# with AUTH_MODE=local; authenticated by the password / refresh token in the body) and
# the dev-only login helpers (mounted only with AUTH_MODE=dev); no business data.
PUBLIC_ENDPOINTS: frozenset[str] = frozenset(
    {
        "/api/v1/health",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/dev/users",
        "/api/v1/auth/dev/token",
    }
)
# Authenticated, but acting only on the caller's own profile, session and password
# (needed also by users without any role and - only these - while a temporary password
# must be changed, ADR 0018 §5).
SELF_ENDPOINTS: frozenset[str] = frozenset(
    {"/api/v1/me", "/api/v1/auth/logout", "/api/v1/auth/password"}
)


# Actions that only read data. Only these may be combined with ``admin_action`` (the
# administrative path skips the check of the endpoint's own action - for a write or an
# approval that would bypass the matrix and the segregation of duties, §5).
READ_ACTIONS: frozenset[Action] = frozenset({Action.REGISTER_VIEW})


# ``POST .../changes/{id}/actions/{action}`` (CLAUDE.md §8): the matrix row of each change
# action (§5). The state machine then checks the actor against the change itself (author,
# assignee, designated approver, four eyes, CI owner - ADR 0012 §4). ``consent`` is given
# by the CI owner, whatever their role in the company (ADR 0012 §5), hence the read row.
CHANGE_ACTION_PERMISSIONS: MappingProxyType[str, Action] = MappingProxyType(
    {
        "submit": Action.CHANGE_EDIT_DRAFT,
        "cancel": Action.CHANGE_EDIT_DRAFT,
        "implement": Action.CHANGE_EDIT_DRAFT,
        "verify": Action.CHANGE_EDIT_DRAFT,
        "rollback": Action.CHANGE_EDIT_DRAFT,
        "approve": Action.CHANGE_APPROVE,
        "reject": Action.CHANGE_APPROVE,
        "return": Action.CHANGE_APPROVE,
        "consent": Action.REGISTER_VIEW,
    }
)


# Report exports (§5 "Eksport PDF/CSV"): the matrix row of each report kind. The editor
# exports only the change card; a multi-company report needs the auditor role in each of
# its companies (§5: "Auditor ... generować raport zbiorczy", ADR 0017 §2).
REPORT_KIND_PERMISSIONS: MappingProxyType[str, Action] = MappingProxyType(
    {"register": Action.EXPORT_REGISTER, "change_card": Action.EXPORT_CHANGE_CARD}
)
AGGREGATE_REPORT_ROLE = Role.AUDITOR


def is_allowed(role: Role, action: Action) -> bool:
    return role in PERMISSIONS[action]


def any_allowed(roles: Iterable[Role], action: Action) -> bool:
    return any(is_allowed(role, action) for role in roles)


# --------------------------------------------------------------------------- declarations


@dataclass(frozen=True, slots=True)
class AccessRule:
    """What a route declares (introspected by the RBAC tests)."""

    action: Action
    kind: Literal[
        "global", "company", "admin_company", "listing", "audit_chain", "any_company", "report"
    ]
    admin_action: Action | None = None
    # The admin path is the narrow READ-ONLY path, only for an admin without membership.
    admin_read_only: bool = False
    # Routes whose required action depends on a path parameter (change actions):
    # ((value, action), ...); ``action`` above is then the action every value needs.
    per_value: tuple[tuple[str, Action], ...] = ()


_RULE_ATTRIBUTE = "__access_rule__"


def _declare(rule: AccessRule, dependency: Callable[..., Any]) -> Any:
    """``Depends(dependency)`` tagged with ``rule``; typed ``Any`` like ``fastapi.Depends``,
    so it can be the default of a parameter annotated with the dependency's result type.

    The resolved user / company is bound to the request's log lines (``app.logs``,
    ADR 0019 §4); FastAPI reads the signature through ``functools.wraps``."""
    from app.logs import bind_principal

    @functools.wraps(dependency)
    async def logged(*args: Any, **kwargs: Any) -> Any:
        result = await dependency(*args, **kwargs)
        bind_principal(result)
        return result

    setattr(logged, _RULE_ATTRIBUTE, rule)
    return Depends(logged)


def access_rules(dependant: "Dependant") -> list[AccessRule]:
    """Access rules declared in a dependency tree (searched recursively)."""
    found: list[AccessRule] = []
    stack = list(dependant.dependencies)
    while stack:
        current = stack.pop()
        rule = getattr(current.call, _RULE_ATTRIBUTE, None)
        if isinstance(rule, AccessRule) and rule not in found:
            found.append(rule)
        stack.extend(current.dependencies)
    return found


@dataclass(frozen=True, slots=True)
class RouteDeclaration:
    path: str
    methods: frozenset[str]
    rules: tuple[AccessRule, ...]


def route_declarations(app: "FastAPI") -> list[RouteDeclaration]:
    """Every API route of ``app`` with its declared access rules (incl. included routers)."""
    from fastapi.routing import APIRoute, iter_route_contexts

    result = []
    for context in iter_route_contexts(app.routes):
        if not isinstance(context.original_route, APIRoute):
            continue  # docs / openapi (Starlette routes, no business data)
        result.append(
            RouteDeclaration(
                path=str(context.path),
                methods=frozenset(context.methods or ()),
                rules=tuple(access_rules(context.dependant)),
            )
        )
    return result


def _check_admin_action(action: Action, admin_action: Action | None) -> None:
    """Fail fast when a route is declared with an unsafe ``admin_action``.

    The administrative path replaces the check of ``action`` by a check of
    ``admin_action``. That is safe for read actions, and for ``admin_action == action``
    when ``app_admin`` holds that action in the matrix (nothing is skipped: the admin is
    checked against the very same action, e.g. ``ci.manage``). Anything else would let the
    admin path bypass the matrix and the segregation of duties (§5).
    """
    if admin_action is None:
        return
    if not is_allowed(Role.APP_ADMIN, admin_action):
        raise ValueError(f"admin_action {admin_action.value!r} is not an app_admin action")
    if action not in READ_ACTIONS and admin_action != action:
        raise ValueError(
            f"admin_action is allowed only for read actions {sorted(READ_ACTIONS)} or when "
            f"it equals the endpoint's own action, not {admin_action.value!r} for "
            f"{action.value!r}"
        )


def forbidden() -> Exception:
    from app.errors import ProblemError

    return ProblemError(
        status=403,
        code="auth.forbidden",
        detail="Brak uprawnień do wykonania tej operacji.",
    )


def company_not_found() -> Exception:
    from app.errors import ProblemError

    return ProblemError(
        status=404,
        code="company.not_found",
        detail="Nie znaleziono spółki.",
    )


# --------------------------------------------------------------------------- dependencies
# Imports of app.auth / app.db / app.services are local: those modules import ``Role``
# from here, so importing them at module level would be circular.


def require(action: Action) -> Any:
    """Global action (no company in the path). Returns the ``CurrentUser``."""
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import CurrentUser
    from app.db import SessionDep, apply_company_scope

    async def dependency(
        request: Request, user: CurrentUserDep, session: SessionDep
    ) -> CurrentUser:
        if not any_allowed(user.global_roles, action):
            await record_access_denied(request, session, user=user, status=403, reason=action.value)
            raise forbidden()
        # Only app_admin is a global role: this is the explicit administrative path.
        await apply_company_scope(
            session, user.company_ids, global_audit_read=user.global_audit_read, admin_scope=True
        )
        return user

    return _declare(AccessRule(action, "global"), dependency)


def require_admin_company(action: Action) -> Any:
    """Administrative action on the company ``{company_id}``. Returns ``CompanyContext``."""
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.db import SessionDep

    async def dependency(
        request: Request, company_id: UUID, user: CurrentUserDep, session: SessionDep
    ) -> CompanyContext:
        if not any_allowed(user.global_roles, action):
            await record_access_denied(
                request,
                session,
                user=user,
                status=403,
                reason=action.value,
                company_id=company_id,
            )
            raise forbidden()
        return await _admin_context(request, session, user, company_id)

    return _declare(AccessRule(action, "admin_company"), dependency)


async def _member_context(
    request: Request,
    session: "AsyncSession",
    user: "CurrentUser",
    company_id: UUID,
    action: Action,
) -> "CompanyContext":
    """``get_company_context``: membership (else 404, §7.3), then the action (else 403).

    Both denials are recorded (``access_denied``, global chain, CLAUDE.md §6.5) in a
    separate transaction before the request fails.
    """
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.services import companies as companies_service

    membership = user.roles_in(company_id)
    company = await companies_service.get_company(session, company_id) if membership else None
    if company is None:
        # No membership (or no such company): 404, never 403 — do not reveal existence.
        await record_access_denied(
            request,
            session,
            user=user,
            status=404,
            reason="no_membership",
            company_id=company_id,
        )
        raise company_not_found()
    roles = membership | user.global_roles
    if not any_allowed(roles, action):
        await record_access_denied(
            request, session, user=user, status=403, reason=action.value, company_id=company_id
        )
        raise forbidden()
    return CompanyContext(company=company, user=user, roles=roles)


def require_company(
    action: Action, *, admin_action: Action | None = None, admin_read_only: bool = False
) -> Any:
    """``get_company_context(company_id)`` + action check. Returns ``CompanyContext``.

    ``admin_action``: if the user is an app admin allowed to perform it, the explicit
    administrative path is used instead (no membership needed). Without it, an app admin
    without membership gets 404 like everybody else. ``action`` must then be one of
    ``READ_ACTIONS`` (``ValueError`` at declaration otherwise).

    ``admin_read_only``: the admin path is the NARROW read path
    (:func:`_admin_read_context`): scope = that company only, no ``admin_scope``, the
    transaction switched to READ ONLY (ADR 0015 §7, ADR 0016). It is taken only by an
    admin WITHOUT a membership in the company: an admin with a role there is resolved by
    :func:`_member_context` like any member (their roles decide, the transaction stays
    writable for what those roles allow).
    """
    _check_admin_action(action, admin_action)
    if admin_read_only and (admin_action is None or action not in READ_ACTIONS):
        raise ValueError("admin_read_only needs admin_action and a read action")
    from app.auth.dependencies import CurrentUserDep
    from app.auth.principal import CompanyContext
    from app.db import SessionDep

    async def dependency(
        request: Request, company_id: UUID, user: CurrentUserDep, session: SessionDep
    ) -> CompanyContext:
        if admin_action is not None and any_allowed(user.global_roles, admin_action):
            if admin_read_only:
                if user.roles_in(company_id):
                    return await _member_context(request, session, user, company_id, action)
                return await _admin_read_context(request, session, user, company_id)
            # A write on the admin path (admin_action == action, e.g. ci.manage) gets only
            # the target company in its scope, WITHOUT app.admin_scope: the policies of the
            # company's own tables need nothing more, and companies, memberships and the
            # dictionaries stay read-only for this transaction (ADR 0011 §1).
            return await _admin_context(
                request, session, user, company_id, admin_scope=action in READ_ACTIONS
            )
        return await _member_context(request, session, user, company_id, action)

    return _declare(
        AccessRule(action, "company", admin_action, admin_read_only=admin_read_only), dependency
    )


def require_register_read() -> Any:
    """Read of the change register of ``{company_id}`` (``register.view``): the list, the
    card (by id and by number), readiness, the change audit trail, the attachment LIST
    (metadata with sha256) and the register tiles. Returns ``CompanyContext``.

    Members: by their roles (404 without membership, §7.3). An app admin WITHOUT a role in
    the company: the named narrow administrative read path (owner decision 2026-11-02,
    variant "a", ADR 0016) - :func:`_admin_read_context`: RLS scope = that company only,
    no ``admin_scope``, READ ONLY transaction, ``CompanyContext.read_only`` set (the card
    then offers no actions and no editable fields). ``app_admin`` holds ``register.view``
    in the matrix (§5), so nothing is skipped. NOT used by the attachment download (it
    writes an audit entry) nor by any write: there the admin without a role still gets
    404 + ``access_denied``.
    """
    return require_company(
        Action.REGISTER_VIEW, admin_action=Action.REGISTER_VIEW, admin_read_only=True
    )


def require_audit_chain(
    action: Action, *, admin_any_company: bool = False, admin_read_any_company: bool = False
) -> Any:
    """One audit chain chosen by the OPTIONAL query parameter ``company_id``.

    Returns ``AuditChainContext`` (ADR 0009):

    - ``company_id`` omitted: the GLOBAL chain. Only app admins (``global_audit_read``,
      ADR 0006 §6 / ADR 0008 §6); everybody else gets 403 (the global chain always
      exists, so the answer reveals nothing);
    - ``company_id`` given: the company's chain through ``get_company_context`` (membership,
      else 404 like for a non-existent company; then ``action`` on the roles, else 403);
    - ``admin_any_company``: an app admin allowed to perform ``action`` may instead use the
      explicit administrative path for ANY existing company (no membership needed; the
      transaction scope is widened with that company only). Used by the chain
      verification, which returns only the verdict, never the entries;
    - ``admin_read_any_company``: an app admin allowed to perform ``action`` reads ANY
      existing company chain on the narrow read path (:func:`_admin_read_context`: only
      that company in scope, no ``admin_scope``, READ ONLY transaction). Used by browsing
      the log (owner decision 2026-11-02, ADR 0009 §3 / ADR 0015 §7).
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import AuditChainContext
    from app.db import SessionDep

    async def dependency(
        request: Request,
        user: CurrentUserDep,
        session: SessionDep,
        company_id: UUID | None = None,
    ) -> AuditChainContext:
        if company_id is None:
            if not (any_allowed(user.global_roles, action) and user.global_audit_read):
                await record_access_denied(
                    request, session, user=user, status=403, reason=f"{action.value}:global"
                )
                raise forbidden()
            return AuditChainContext(user=user, company=None, roles=user.global_roles)
        if admin_read_any_company and any_allowed(user.global_roles, action):
            ctx = await _admin_read_context(request, session, user, company_id)
        elif admin_any_company and any_allowed(user.global_roles, action):
            ctx = await _admin_context(request, session, user, company_id)
        else:
            ctx = await _member_context(request, session, user, company_id, action)
        return AuditChainContext(
            user=user, company=ctx.company, roles=ctx.roles, admin_path=ctx.admin_path
        )

    return _declare(AccessRule(action, "audit_chain"), dependency)


def require_change_action() -> Any:
    """Membership in ``{company_id}`` (else 404, also for app admins - no admin path: the
    admin performs no change actions, §5), then the matrix action mapped from the path
    parameter ``action`` (:data:`CHANGE_ACTION_PERMISSIONS`, else 403). An unknown action
    is 404 (no such route). Returns ``CompanyContext``."""
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.db import SessionDep
    from app.errors import ProblemError

    async def dependency(
        request: Request, company_id: UUID, action: str, user: CurrentUserDep, session: SessionDep
    ) -> CompanyContext:
        ctx = await _member_context(request, session, user, company_id, Action.REGISTER_VIEW)
        required = CHANGE_ACTION_PERMISSIONS.get(action)
        if required is None:
            raise ProblemError(
                status=404, code="change.unknown_action", detail="Nieznana akcja zmiany."
            )
        if not any_allowed(ctx.roles, required):
            await record_access_denied(
                request,
                session,
                user=user,
                status=403,
                reason=f"{required.value}:{action}",
                company_id=company_id,
            )
            raise forbidden()
        return ctx

    rule = AccessRule(
        Action.REGISTER_VIEW, "company", per_value=tuple(CHANGE_ACTION_PERMISSIONS.items())
    )
    return _declare(rule, dependency)


def require_in_any_company(action: Action) -> Any:
    """Global read of a shared dictionary (no company in the path). Returns ``CurrentUser``.

    Allowed when ``action`` is allowed by the user's global roles or by the roles in at
    least one company; otherwise 403 (recorded like every denial). Unlike :func:`require`
    it does NOT open the admin scope: the transaction keeps the membership scope.
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import CurrentUser
    from app.db import SessionDep

    async def dependency(
        request: Request, user: CurrentUserDep, session: SessionDep
    ) -> CurrentUser:
        if not any_allowed(user.global_roles, action) and not any(
            any_allowed(user.roles_in(cid), action) for cid in user.company_ids
        ):
            await record_access_denied(request, session, user=user, status=403, reason=action.value)
            raise forbidden()
        return user

    return _declare(AccessRule(action, "any_company"), dependency)


@dataclass(frozen=True, slots=True)
class CompanyVisibility:
    """Result of :func:`visible_companies`: all companies (admin path) or the listed ones."""

    all: bool
    company_ids: frozenset[UUID]
    user: "CurrentUser"


def visible_companies(action: Action, *, admin_action: Action | None = None) -> Any:
    """For list endpoints: companies in which the user may perform ``action``.

    ``admin_action``: an app admin allowed to perform it sees all companies; only for
    ``READ_ACTIONS`` (``ValueError`` at declaration otherwise).
    """
    _check_admin_action(action, admin_action)
    from app.auth.dependencies import CurrentUserDep
    from app.db import SessionDep, apply_company_scope

    async def dependency(user: CurrentUserDep, session: SessionDep) -> CompanyVisibility:
        if admin_action is not None and any_allowed(user.global_roles, admin_action):
            await apply_company_scope(
                session,
                user.company_ids,
                global_audit_read=user.global_audit_read,
                admin_scope=True,
            )
            return CompanyVisibility(all=True, company_ids=frozenset(), user=user)
        ids = frozenset(
            cid
            for cid in user.company_ids
            if any_allowed(user.roles_in(cid) | user.global_roles, action)
        )
        return CompanyVisibility(all=False, company_ids=ids, user=user)

    return _declare(AccessRule(action, "listing", admin_action), dependency)


async def _admin_context(
    request: Request,
    session: "AsyncSession",
    user: "CurrentUser",
    company_id: UUID,
    *,
    admin_scope: bool = True,
) -> "CompanyContext":
    """Explicit administrative path for one company (ADR 0007).

    The transaction scope is widened with the target company (so its audit chain can be
    written, e.g. role grants) and ``app.admin_scope`` is switched on - unless
    ``admin_scope=False`` (company-scoped writes the admin holds in the matrix, e.g. the
    CI inventory: the widened scope alone is enough and nothing global is writable). A
    non-existent company is a 404 recorded like every other denial (``access_denied``,
    reason ``not_found``).
    """
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.db import apply_company_scope
    from app.services import companies as companies_service

    # The scope must be applied BEFORE the lookup: without membership the company row is
    # visible only on the admin path (RLS, ADR 0008). For a non-existent id the widened
    # scope is harmless: the request fails with 404 and its transaction is rolled back.
    await apply_company_scope(
        session,
        [*user.company_ids, company_id],
        global_audit_read=user.global_audit_read,
        admin_scope=admin_scope,
    )
    company = await companies_service.get_company(session, company_id)
    if company is None:
        await record_access_denied(
            request, session, user=user, status=404, reason="not_found", company_id=company_id
        )
        raise company_not_found()
    return CompanyContext(
        company=company,
        user=user,
        roles=user.roles_in(company_id) | user.global_roles,
        admin_path=True,
    )


async def _admin_read_context(
    request: Request,
    session: "AsyncSession",
    user: "CurrentUser",
    company_id: UUID,
) -> "CompanyContext":
    """NARROW administrative READ path for one company (ADR 0015 §7, ADR 0016).

    Unlike :func:`_admin_context`, the transaction scope is REPLACED by that single company
    (not added to the admin's memberships), ``app.admin_scope`` and the global audit read
    stay off, and the transaction is switched to READ ONLY before anything is read - so
    nothing can be written in it, whatever the RLS policies of the company allow. A
    non-existent company is a 404 recorded like every denial (separate transaction).
    """
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.db import apply_company_scope, set_transaction_read_only
    from app.services import companies as companies_service

    await apply_company_scope(session, [company_id], global_audit_read=False, admin_scope=False)
    await set_transaction_read_only(session)
    company = await companies_service.get_company(session, company_id)
    if company is None:
        await record_access_denied(
            request, session, user=user, status=404, reason="not_found", company_id=company_id
        )
        raise company_not_found()
    return CompanyContext(
        company=company,
        user=user,
        roles=user.roles_in(company_id) | user.global_roles,
        admin_path=True,
        read_only=True,
    )


async def _admin_export_context(
    request: Request,
    session: "AsyncSession",
    user: "CurrentUser",
    company_id: UUID,
) -> "CompanyContext":
    """Named administrative EXPORT path for one company (ADR 0017 §4, §14): an app admin
    WITHOUT a role there exports it (§5 gives the admin the export).

    Like :func:`_admin_read_context` the transaction scope is REPLACED by that single
    company (not the admin's memberships + it), with no ``app.admin_scope`` and no global
    audit read - but the transaction stays writable: the export writes its
    ``report_exports`` row and the audit entry in that company's chain, and nothing else
    is in reach. A non-existent company is a 404 recorded like every denial.
    """
    from app.auth.events import record_access_denied
    from app.auth.principal import CompanyContext
    from app.db import apply_company_scope
    from app.services import companies as companies_service

    await apply_company_scope(session, [company_id], global_audit_read=False, admin_scope=False)
    company = await companies_service.get_company(session, company_id)
    if company is None:
        await record_access_denied(
            request, session, user=user, status=404, reason="not_found", company_id=company_id
        )
        raise company_not_found()
    return CompanyContext(
        company=company,
        user=user,
        roles=user.roles_in(company_id) | user.global_roles,
        admin_path=True,
    )


def require_register_export() -> Any:
    """``GET /companies/{company_id}/changes/export.csv`` (``export.register``).

    Members by their roles (:func:`_member_context`; also an app admin WITH a role in the
    company - consistent with ADR 0016); an app admin without a role takes the named admin
    export path (:func:`_admin_export_context`: that company only, no ``admin_scope``).
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.principal import CompanyContext
    from app.db import SessionDep

    action = Action.EXPORT_REGISTER

    async def dependency(
        request: Request, company_id: UUID, user: CurrentUserDep, session: SessionDep
    ) -> CompanyContext:
        if not user.roles_in(company_id) and any_allowed(user.global_roles, action):
            return await _admin_export_context(request, session, user, company_id)
        return await _member_context(request, session, user, company_id, action)

    _check_admin_action(action, action)
    return _declare(AccessRule(action, "company", action), dependency)


# --------------------------------------------------------------------------- reports


def _report_rule() -> AccessRule:
    return AccessRule(
        Action.EXPORT_CHANGE_CARD,
        "report",
        # app_admin holds both export rows (§5): the admin export path skips nothing.
        admin_action=Action.EXPORT_CHANGE_CARD,
        per_value=tuple(REPORT_KIND_PERMISSIONS.items()),
    )


def report_not_found() -> Exception:
    from app.errors import ProblemError

    return ProblemError(status=404, code="report.not_found", detail="Nie znaleziono raportu.")


def _aggregate_companies(user: "CurrentUser") -> list[UUID]:
    """Companies of a multi-company report: those where the user is an auditor."""
    return [cid for cid in user.company_ids if AGGREGATE_REPORT_ROLE in user.roles_in(cid)]


def require_report_order() -> Any:
    """``POST /reports`` (body ``ReportCreate``). Returns ``ReportOrder`` (ADR 0017 §2).

    - ``company_id`` given: membership in it (else 404 ``company.not_found``, §7.3) and the
      action of the kind (:data:`REPORT_KIND_PERMISSIONS`, else 403). An app admin WITHOUT a
      role there takes the named admin EXPORT path (:func:`_admin_export_context`: the
      scope is that company only, no ``admin_scope``, no global audit read, so the export
      can be recorded in its chain and in ``report_exports``; nothing else is in reach).
      §5 gives ``app_admin`` the export, so nothing is skipped;
    - ``company_id`` null: the multi-company register report of an auditor - every company
      where the user has the auditor role (all already in the request scope); none -> 403.
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import ReportOrder
    from app.db import SessionDep
    from app.errors import ProblemError
    from app.schemas.reports import ReportCreate
    from app.services import companies as companies_service

    async def dependency(
        request: Request, body: ReportCreate, user: CurrentUserDep, session: SessionDep
    ) -> ReportOrder:
        action = REPORT_KIND_PERMISSIONS[body.kind]
        if body.company_id is None:
            if body.kind != "register":
                raise ProblemError(
                    status=422,
                    code="report.invalid_kind",
                    detail="Kartę zmiany można wygenerować tylko dla jednej spółki.",
                    extra={"fields": ["company_id"]},
                )
            ids = _aggregate_companies(user)
            if not ids:
                await record_access_denied(
                    request, session, user=user, status=403, reason=f"{action.value}:all"
                )
                raise forbidden()
            found = [await companies_service.get_company(session, cid) for cid in ids]
            companies = tuple(sorted((c for c in found if c), key=lambda c: c.prefix))
            return ReportOrder(user=user, company=None, companies=companies, body=body)
        if not user.roles_in(body.company_id) and any_allowed(user.global_roles, action):
            ctx = await _admin_export_context(request, session, user, body.company_id)
            return ReportOrder(
                user=user,
                company=ctx.company,
                companies=(ctx.company,),
                body=body,
                admin_path=True,
            )
        ctx = await _member_context(request, session, user, body.company_id, action)
        return ReportOrder(user=user, company=ctx.company, companies=(ctx.company,), body=body)

    return _declare(_report_rule(), dependency)


def require_report_list() -> Any:
    """``GET /reports[?company_id=]`` - the report list of the screen "Raporty i eksport".
    Returns ``ReportListing``.

    - ``company_id`` given: membership (else 404, §7.3), then ``export.change_card`` (the
      broadest export row, else 403); an app admin without a role reads that company on the
      narrow READ-ONLY admin path (:func:`_admin_read_context`);
    - omitted: every company where the user may export (none -> 403) and the user's own
      multi-company reports; an app admin lists every report (``admin_scope``, READ ONLY
      transaction - RLS lets the admin path read every row, never write).
    Register reports are listed only where the user has ``export.register``; elsewhere only
    change cards (the editor).
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import ReportListing
    from app.db import SessionDep, apply_company_scope, set_transaction_read_only

    async def dependency(
        request: Request,
        user: CurrentUserDep,
        session: SessionDep,
        company_id: UUID | None = None,
    ) -> ReportListing:
        is_admin = any_allowed(user.global_roles, Action.EXPORT_REGISTER)
        if company_id is not None:
            if is_admin and not user.roles_in(company_id):
                await _admin_read_context(request, session, user, company_id)
                return ReportListing(user, company_id, True, frozenset(), frozenset())
            ctx = await _member_context(
                request, session, user, company_id, Action.EXPORT_CHANGE_CARD
            )
            await set_transaction_read_only(session)
            if is_admin or any_allowed(ctx.roles, Action.EXPORT_REGISTER):
                return ReportListing(user, company_id, False, frozenset({company_id}), frozenset())
            return ReportListing(user, company_id, False, frozenset(), frozenset({company_id}))
        if is_admin:
            await apply_company_scope(
                session, user.company_ids, global_audit_read=False, admin_scope=True
            )
            await set_transaction_read_only(session)
            return ReportListing(user, None, True, frozenset(), frozenset())
        register = frozenset(
            cid
            for cid in user.company_ids
            if any_allowed(user.roles_in(cid), Action.EXPORT_REGISTER)
        )
        cards = (
            frozenset(
                cid
                for cid in user.company_ids
                if any_allowed(user.roles_in(cid), Action.EXPORT_CHANGE_CARD)
            )
            - register
        )
        if not register and not cards:
            await record_access_denied(
                request, session, user=user, status=403, reason=Action.EXPORT_CHANGE_CARD.value
            )
            raise forbidden()
        await set_transaction_read_only(session)
        return ReportListing(user, None, False, register, cards)

    return _declare(_report_rule(), dependency)


def require_report(*, download: bool) -> Any:
    """``GET /reports/{report_id}`` (status) and ``.../download``. Returns ``ReportAccess``.

    The report is looked up in the request scope (RLS: rows of the user's companies and
    the user's own multi-company reports; an app admin: every row on the admin path). Not
    visible -> 404 ``report.not_found`` (also a report of a foreign company - existence is
    not revealed). Visible:

    - company report: the action of its kind in that company (else 403, recorded);
    - multi-company report (only its author sees it): the auditor role in EVERY company of
      the report now (a lost role -> 403, recorded);
    - app admin: always (§5); a download REPLACES the scope by the companies of the
      report, WITHOUT ``admin_scope`` (named admin export path: the download is recorded
      in their chains, nothing else is in reach). The status read is switched to READ
      ONLY. ``admin_path``: the admin lacks a role in a company of the report.
    """
    from app.auth.dependencies import CurrentUserDep
    from app.auth.events import record_access_denied
    from app.auth.principal import ReportAccess
    from app.db import SessionDep, apply_company_scope, set_transaction_read_only
    from app.services import reports as reports_service

    async def dependency(
        request: Request, report_id: UUID, user: CurrentUserDep, session: SessionDep
    ) -> ReportAccess:
        is_admin = any_allowed(user.global_roles, Action.EXPORT_REGISTER)
        if is_admin:
            await apply_company_scope(
                session, user.company_ids, global_audit_read=False, admin_scope=True
            )
        report = await reports_service.get_report(session, report_id)
        if report is None:
            raise report_not_found()
        action = REPORT_KIND_PERMISSIONS[report.kind]
        if is_admin:
            admin_path = any(not user.roles_in(cid) for cid in report.scope_company_ids)
            if download:
                await apply_company_scope(
                    session, report.scope_company_ids, global_audit_read=False, admin_scope=False
                )
            else:
                await set_transaction_read_only(session)
            return ReportAccess(user=user, report=report, admin_path=admin_path)
        if report.company_id is None:
            allowed = report.generated_by_id == user.id and all(
                AGGREGATE_REPORT_ROLE in user.roles_in(cid) for cid in report.scope_company_ids
            )
            target = None
        else:
            allowed = any_allowed(user.roles_in(report.company_id), action)
            target = report.company_id
        if not allowed:
            await record_access_denied(
                request, session, user=user, status=403, reason=action.value, company_id=target
            )
            raise forbidden()
        if not download:
            await set_transaction_read_only(session)
        return ReportAccess(user=user, report=report)

    return _declare(_report_rule(), dependency)
