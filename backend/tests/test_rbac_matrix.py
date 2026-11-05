"""RBAC: every route declares an action (or is public / self), and the full matrix per persona.

Personas (tests.factories.World): app admin without membership, approver / editor /
auditor / viewer of company A, outsider (member of company B only), nobody (no roles).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.db import SessionDep
from app.main import create_app
from app.permissions import (
    PUBLIC_ENDPOINTS,
    SELF_ENDPOINTS,
    Action,
    require_company,
    route_declarations,
)
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import DbUrls, make_settings
from tests.factories import (
    PERSONAS,
    World,
    add_changes,
    add_report,
    auth,
    client_for,
    random_category_code,
    random_ci_type_code,
    random_prefix,
)
from tests.test_api_auth import assert_problem


@pytest.mark.parametrize("auth_mode", ["dev", "local"])
def test_every_route_declares_an_action_or_is_public(auth_mode: str) -> None:
    settings = make_settings(
        auth_mode=auth_mode,
        dev_auth_secret=None if auth_mode == "local" else make_settings().dev_auth_secret,
        auth_jwt_secret=LOCAL_SECRET,
    )
    app = create_app(settings)
    undeclared = []
    routes = route_declarations(app)
    assert len(routes) >= 8
    for route in routes:
        rules = route.rules
        exempt = route.path in PUBLIC_ENDPOINTS or route.path in SELF_ENDPOINTS
        if exempt and rules:
            undeclared.append(f"{route.path}: both exempt and declared")
        elif not exempt and not rules:
            undeclared.append(f"{sorted(route.methods)} {route.path}")
    assert undeclared == []


def test_public_and_self_endpoints() -> None:
    assert set(PUBLIC_ENDPOINTS) == {
        "/api/v1/health",
        "/api/v1/auth/dev/users",
        "/api/v1/auth/dev/token",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
    }
    assert set(SELF_ENDPOINTS) == {"/api/v1/me", "/api/v1/auth/logout", "/api/v1/auth/password"}


def test_auth_routes_depend_on_the_mode() -> None:
    """Local accounts (ADR 0018): login/refresh/logout/password only with AUTH_MODE=local,
    the dev login only with AUTH_MODE=dev; everything else is the same in both modes."""

    def paths(mode: str) -> set[str]:
        app = create_app(
            make_settings(
                auth_mode=mode,
                dev_auth_secret=None if mode == "local" else make_settings().dev_auth_secret,
                auth_jwt_secret=LOCAL_SECRET,
            )
        )
        return {r.path for r in route_declarations(app)}

    local, dev = paths("local"), paths("dev")
    assert local - dev == {
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
        "/api/v1/auth/password",
    }
    assert dev - local == {"/api/v1/auth/dev/users", "/api/v1/auth/dev/token"}


def test_declared_actions() -> None:
    app = create_app(make_settings())
    routes = route_declarations(app)
    declared = {
        (method, route.path): [r.action for r in route.rules]
        for route in routes
        for method in route.methods
    }
    assert declared[("GET", "/api/v1/companies")] == [Action.REGISTER_VIEW]
    assert declared[("POST", "/api/v1/companies")] == [Action.COMPANY_MANAGE]
    assert declared[("PATCH", "/api/v1/companies/{company_id}")] == [Action.COMPANY_MANAGE]
    assert declared[("POST", "/api/v1/companies/{company_id}/archive")] == [Action.COMPANY_MANAGE]
    assert declared[("GET", "/api/v1/companies/{company_id}/members")] == [Action.REGISTER_VIEW]
    assert declared[("PUT", "/api/v1/companies/{company_id}/members/{user_id}")] == [
        Action.MEMBERSHIP_MANAGE
    ]
    assert declared[("GET", "/api/v1/users")] == [Action.MEMBERSHIP_MANAGE]
    # Stage 6 (ADR 0015): admin read models.
    assert declared[("GET", "/api/v1/users/{user_id}")] == [Action.MEMBERSHIP_MANAGE]
    # Stage 8 (ADR 0018): local accounts.
    assert declared[("POST", "/api/v1/users")] == [Action.USER_MANAGE]
    assert declared[("POST", "/api/v1/users/{user_id}/reset-password")] == [Action.USER_MANAGE]
    assert declared[("PATCH", "/api/v1/users/{user_id}")] == [Action.USER_MANAGE]
    assert declared[("GET", "/api/v1/permissions/matrix")] == [Action.REGISTER_VIEW]
    (rule,) = next(r for r in routes if r.path == "/api/v1/permissions/matrix").rules
    assert rule.kind == "any_company"
    rule = next(r for r in routes if r.path == "/api/v1/companies/{company_id}/members").rules[0]
    assert rule.admin_action == Action.MEMBERSHIP_MANAGE
    assert declared[("POST", "/api/v1/audit/verify")] == [Action.AUDIT_VERIFY]
    assert declared[("GET", "/api/v1/audit")] == [Action.AUDIT_READ]
    for path in ("/api/v1/audit/verify", "/api/v1/audit"):
        (rule,) = next(r for r in routes if r.path == path).rules
        assert rule.kind == "audit_chain"
    # Stage 3 (ADR 0011): dictionaries, company categories, CI inventory.
    for path in ("/api/v1/categories", "/api/v1/ci-types"):
        assert declared[("GET", path)] == [Action.REGISTER_VIEW]
        assert declared[("POST", path)] == [Action.DICTIONARY_MANAGE]
        (rule,) = next(r for r in routes if r.path == path).rules
        assert rule.kind in {"any_company", "global"}
    assert declared[("PATCH", "/api/v1/categories/{category_id}")] == [Action.DICTIONARY_MANAGE]
    assert declared[("PATCH", "/api/v1/ci-types/{ci_type_id}")] == [Action.DICTIONARY_MANAGE]
    company = "/api/v1/companies/{company_id}"
    assert declared[("GET", f"{company}/categories")] == [Action.REGISTER_VIEW]
    assert declared[("PUT", f"{company}/categories")] == [Action.COMPANY_MANAGE]
    assert declared[("GET", f"{company}/ci")] == [Action.REGISTER_VIEW]
    assert declared[("GET", f"{company}/ci/{{ci_id}}")] == [Action.REGISTER_VIEW]
    assert declared[("POST", f"{company}/ci")] == [Action.CI_MANAGE]
    assert declared[("PATCH", f"{company}/ci/{{ci_id}}")] == [Action.CI_MANAGE]
    # Change register reads: the named admin read-only path (ADR 0016); the download, the
    # writes and the actions have no admin path.
    change = f"{company}/changes/{{change_id}}"
    for path in (
        f"{company}/changes",
        f"{company}/changes/by-number/{{number}}",
        change,
        f"{change}/readiness",
        f"{change}/audit",
        f"{change}/attachments",
        f"{company}/stats",
    ):
        (rule,) = next(r for r in routes if r.path == path and "GET" in r.methods).rules
        assert rule.action == Action.REGISTER_VIEW, path
        assert rule.admin_action == Action.REGISTER_VIEW, path
        assert rule.admin_read_only, path
    for route in routes:
        if route.path.startswith(f"{company}/changes") and (
            route.methods & {"POST", "PATCH", "PUT", "DELETE"}
            or route.path == f"{change}/attachments/{{attachment_id}}"
        ):
            for rule in route.rules:
                assert rule.admin_action is None, route.path
    for path, admin_action in (
        (f"{company}/categories", Action.COMPANY_MANAGE),
        (f"{company}/ci", Action.CI_MANAGE),
        (f"{company}/ci/{{ci_id}}", Action.CI_MANAGE),
    ):
        for rule in next(r for r in routes if r.path == path).rules:
            if rule.kind == "company":
                assert rule.admin_action == admin_action, path


def test_audit_actions_in_the_matrix() -> None:
    """CLAUDE.md §5: verification and browsing the whole log - app admin and auditor."""
    from app.permissions import PERMISSIONS, Role

    expected = frozenset({Role.APP_ADMIN, Role.AUDITOR})
    assert PERMISSIONS[Action.AUDIT_VERIFY] == expected
    assert PERMISSIONS[Action.AUDIT_READ] == expected


# --------------------------------------------------------------------------- matrix (database)


@pytest.fixture
async def world(world: World, rw_engine: Any) -> World:
    """The shared world plus changes of A and B (``tests.factories.add_changes``)."""
    return await add_report(rw_engine, await add_changes(rw_engine, world))


class Multipart:
    """A request body sent as ``multipart/form-data`` (attachments)."""

    def __init__(self, files: dict[str, Any]) -> None:
        self.files = files


def _send(body: Any) -> dict[str, Any]:
    return {"files": body.files} if isinstance(body, Multipart) else {"json": body}


Request = Callable[[World], tuple[str, str, Any]]


def _change(w: World, suffix: str = "") -> str:
    assert w.draft_a is not None
    return f"/api/v1/companies/{w.a.id}/changes/{w.draft_a.id}{suffix}"


def _pending(w: World, suffix: str = "") -> str:
    assert w.pending_a is not None
    return f"/api/v1/companies/{w.a.id}/changes/{w.pending_a.id}{suffix}"


def _on(w: World, change: Any, suffix: str) -> str:
    assert change is not None
    return f"/api/v1/companies/{w.a.id}/changes/{change.id}{suffix}"


def _number(w: World) -> str:
    assert w.draft_a is not None
    return f"/api/v1/companies/{w.a.id}/changes/by-number/{w.draft_a.number}"


def _download(w: World) -> str:
    assert w.attachment_a is not None
    return _change(w, f"/attachments/{w.attachment_a.id}")


ENDPOINTS: dict[str, Request] = {
    "GET /me": lambda w: ("GET", "/api/v1/me", None),
    "GET /companies": lambda w: ("GET", "/api/v1/companies", None),
    "POST /companies": lambda w: (
        "POST",
        "/api/v1/companies",
        {"name": f"Macierz {random_prefix()}", "prefix": random_prefix()},
    ),
    "PATCH /companies/{id}": lambda w: (
        "PATCH",
        f"/api/v1/companies/{w.a.id}",
        {"is_ksc_entity": True},
    ),
    "POST /companies/{id}/archive": lambda w: ("POST", f"/api/v1/companies/{w.a.id}/archive", None),
    "GET /companies/{id}/members": lambda w: ("GET", f"/api/v1/companies/{w.a.id}/members", None),
    "PUT /companies/{id}/members/{user_id}": lambda w: (
        "PUT",
        f"/api/v1/companies/{w.a.id}/members/{w.nobody.id}",
        {"roles": ["viewer"]},
    ),
    "GET /users": lambda w: ("GET", "/api/v1/users", None),
    "GET /users/{user_id}": lambda w: ("GET", f"/api/v1/users/{w.editor.id}", None),
    "POST /users": lambda w: (
        "POST",
        "/api/v1/users",
        {"email": f"macierz-{uuid4().hex[:10]}@example.com", "display_name": "Konto Macierz"},
    ),
    "POST /users/{user_id}/reset-password": lambda w: (
        "POST",
        f"/api/v1/users/{w.nobody.id}/reset-password",
        None,
    ),
    "PATCH /users/{user_id}": lambda w: (
        "PATCH",
        f"/api/v1/users/{w.nobody.id}",
        {"display_name": f"Norbert {uuid4().hex[:6]}"},
    ),
    "GET /permissions/matrix": lambda w: ("GET", "/api/v1/permissions/matrix", None),
    # Audit chains: ``?company`` = the company chain (query company_id), plain = global.
    "POST /audit/verify": lambda w: ("POST", "/api/v1/audit/verify", None),
    "POST /audit/verify?company": lambda w: (
        "POST",
        f"/api/v1/audit/verify?company_id={w.a.id}",
        None,
    ),
    "GET /audit": lambda w: ("GET", "/api/v1/audit", None),
    "GET /audit?company": lambda w: ("GET", f"/api/v1/audit?company_id={w.a.id}", None),
    # Stage 3: global dictionaries
    "GET /categories": lambda w: ("GET", "/api/v1/categories", None),
    "POST /categories": lambda w: (
        "POST",
        "/api/v1/categories",
        {"code": random_category_code(), "name": "Macierz"},
    ),
    "PATCH /categories/{category_id}": lambda w: (
        "PATCH",
        f"/api/v1/categories/{w.category.id}",
        {"name": f"Macierz {random_prefix()}"},
    ),
    "GET /ci-types": lambda w: ("GET", "/api/v1/ci-types", None),
    "POST /ci-types": lambda w: (
        "POST",
        "/api/v1/ci-types",
        {"code": random_ci_type_code(), "name": "Macierz"},
    ),
    "PATCH /ci-types/{ci_type_id}": lambda w: (
        "PATCH",
        f"/api/v1/ci-types/{w.ci_type.id}",
        {"name": f"Macierz {random_prefix()}"},
    ),
    # Stage 3: company categories and the CI inventory
    "GET /companies/{id}/categories": lambda w: (
        "GET",
        f"/api/v1/companies/{w.a.id}/categories",
        None,
    ),
    "PUT /companies/{id}/categories": lambda w: (
        "PUT",
        f"/api/v1/companies/{w.a.id}/categories",
        {"categories": []},  # add_changes made world.category available: withdraw it
    ),
    "GET /companies/{id}/ci": lambda w: ("GET", f"/api/v1/companies/{w.a.id}/ci", None),
    "POST /companies/{id}/ci": lambda w: (
        "POST",
        f"/api/v1/companies/{w.a.id}/ci",
        {"ci_type_id": str(w.ci_type.id), "identifier": random_prefix(), "name": "Macierz"},
    ),
    "GET /companies/{id}/ci/{ci_id}": lambda w: (
        "GET",
        f"/api/v1/companies/{w.a.id}/ci/{w.ci_a.id}",
        None,
    ),
    "PATCH /companies/{id}/ci/{ci_id}": lambda w: (
        "PATCH",
        f"/api/v1/companies/{w.a.id}/ci/{w.ci_a.id}",
        {"name": f"Macierz {random_prefix()}"},
    ),
    # Stage 4: changes (ADR 0013)
    "GET /companies/{id}/changes": lambda w: ("GET", f"/api/v1/companies/{w.a.id}/changes", None),
    "POST /companies/{id}/changes": lambda w: (
        "POST",
        f"/api/v1/companies/{w.a.id}/changes",
        {"title": "Macierz"},
    ),
    "GET /companies/{id}/changes/by-number/{number}": lambda w: ("GET", _number(w), None),
    "GET /companies/{id}/changes/{change_id}": lambda w: ("GET", _change(w), None),
    "PATCH /companies/{id}/changes/{change_id}": lambda w: (
        "PATCH",
        _change(w),
        {"title": f"Macierz {random_prefix()}", "version": 1},
    ),
    "GET /companies/{id}/changes/{change_id}/readiness": lambda w: (
        "GET",
        _change(w, "/readiness"),
        None,
    ),
    # The matrix row of each action (CHANGE_ACTION_PERMISSIONS), then the state machine:
    # cancel - only the author (the editor); approve - the designated approver; consent -
    # any role passes the matrix, but the category needs no consent (409).
    "POST /companies/{id}/changes/{change_id}/actions/{action}?cancel": lambda w: (
        "POST",
        _change(w, "/actions/cancel"),
        None,
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?approve": lambda w: (
        "POST",
        _pending(w, "/actions/approve"),
        {"version": w.pending_a.version},  # type: ignore[union-attr]
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?submit": lambda w: (
        "POST",
        _change(w, "/actions/submit"),
        None,
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?reject": lambda w: (
        "POST",
        _pending(w, "/actions/reject"),
        {"comment": "Odrzucam (macierz)."},
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?return": lambda w: (
        "POST",
        _pending(w, "/actions/return"),
        {"comment": "Do poprawy (macierz)."},
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?implement": lambda w: (
        "POST",
        _on(w, w.approved_a, "/actions/implement"),
        None,
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?verify": lambda w: (
        "POST",
        _on(w, w.implemented_a, "/actions/verify"),
        None,
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?rollback": lambda w: (
        "POST",
        _on(w, w.implemented_a, "/actions/rollback"),
        {"comment": "Wycofuję (macierz)."},
    ),
    "POST /companies/{id}/changes/{change_id}/actions/{action}?consent": lambda w: (
        "POST",
        _pending(w, "/actions/consent"),
        None,
    ),
    "GET /companies/{id}/changes/{change_id}/audit": lambda w: ("GET", _change(w, "/audit"), None),
    "POST /companies/{id}/changes/{change_id}/comments": lambda w: (
        "POST",
        _change(w, "/comments"),
        {"body": "Komentarz z macierzy"},
    ),
    "GET /companies/{id}/changes/{change_id}/attachments": lambda w: (
        "GET",
        _change(w, "/attachments"),
        None,
    ),
    "POST /companies/{id}/changes/{change_id}/attachments": lambda w: (
        "POST",
        _change(w, "/attachments"),
        Multipart({"file": ("macierz.txt", b"macierz", "text/plain")}),
    ),
    "GET /companies/{id}/changes/{change_id}/attachments/{attachment_id}": lambda w: (
        "GET",
        _download(w),
        None,
    ),
    "GET /companies/{id}/stats": lambda w: ("GET", f"/api/v1/companies/{w.a.id}/stats", None),
    "GET /companies/{id}/audit/status": lambda w: (
        "GET",
        f"/api/v1/companies/{w.a.id}/audit/status",
        None,
    ),
    # Stage 7: report exports (ADR 0017)
    "POST /reports?register": lambda w: ("POST", "/api/v1/reports", _register_body(w, w.a.id)),
    "POST /reports?change_card": lambda w: (
        "POST",
        "/api/v1/reports",
        {"kind": "change_card", "company_id": str(w.a.id), "change_id": str(w.draft_a.id)},  # type: ignore[union-attr]
    ),
    "POST /reports?all": lambda w: ("POST", "/api/v1/reports", _register_body(w, None)),
    "GET /reports": lambda w: ("GET", "/api/v1/reports", None),
    "GET /reports?company": lambda w: ("GET", f"/api/v1/reports?company_id={w.a.id}", None),
    "GET /reports/{report_id}": lambda w: (
        "GET",
        f"/api/v1/reports/{w.report_a.id}",  # type: ignore[union-attr]
        None,
    ),
    "GET /reports/{report_id}/download": lambda w: (
        "GET",
        f"/api/v1/reports/{w.report_a.id}/download",  # type: ignore[union-attr]
        None,
    ),
    "GET /companies/{id}/changes/export.csv": lambda w: (
        "GET",
        f"/api/v1/companies/{w.a.id}/changes/export.csv",
        None,
    ),
}


def _register_body(w: World, company_id: UUID | None) -> dict[str, Any]:
    return {
        "kind": "register",
        "company_id": str(company_id) if company_id else None,
        "period_from": "2000-01-01T00:00:00Z",
        "period_to": "2100-01-01T00:00:00Z",
    }


ALL_OK = dict.fromkeys(PERSONAS, 200)
ADMIN_ONLY = {p: (200 if p == "admin" else 403) for p in PERSONAS}
ADMIN_CREATES = {p: (201 if p == "admin" else 403) for p in PERSONAS}
# Members of A (any role) and the app admin on the admin path; non-members 404 (§7.3).
COMPANY_READ = {**ALL_OK, "outsider": 404, "nobody": 404}
# Shared dictionaries: anybody with a role in ANY company (or the admin); "nobody" 403.
ANY_ROLE = {**ALL_OK, "nobody": 403}
# CI inventory (§5): app admin (admin path), approver, editor; read-only roles 403.
CI_WRITE = {
    "admin": 200,
    "approver": 200,
    "editor": 200,
    "auditor": 403,
    "viewer": 403,
    "outsider": 404,
    "nobody": 404,
}

# Change register reads: members, and the app admin without a role on the named narrow
# read-only path (``require_register_read``, owner decision 2026-11-02, ADR 0016).
REGISTER_READ = COMPANY_READ
# Membership only - the app admin without a role gets 404 like an outsider (§5, ADR 0007
# §4): the attachment download (writes an audit entry) and the change actions.
MEMBER_READ = {**COMPANY_READ, "admin": 404}
CHANGE_WRITE = {
    "admin": 404,
    "approver": 200,
    "editor": 200,
    "auditor": 403,
    "viewer": 403,
    "outsider": 404,
    "nobody": 404,
}
CHANGE_CREATE = {p: (201 if s == 200 else s) for p, s in CHANGE_WRITE.items()}
NO_CONSENT_RULE = (409, "change.invalid_transition")
EXPORT_REGISTER = {
    "admin": 200,
    "approver": 200,
    "editor": 403,
    "auditor": 200,
    "viewer": 403,
    "outsider": 404,
    "nobody": 404,
}
REPORT_CREATE = {p: (201 if s == 200 else s) for p, s in EXPORT_REGISTER.items()}
# A report of A (no company in the path): outsiders cannot see it - 404 report.not_found.
REPORT_NOT_FOUND = (404, "report.not_found")
REPORT_READ = {**EXPORT_REGISTER, "outsider": REPORT_NOT_FOUND, "nobody": REPORT_NOT_FOUND}
Expected = int | tuple[int, str]

# persona -> expected status (CLAUDE.md §5; foreign company -> 404, §7.3); a tuple adds the
# problem code when the state machine (not the matrix) answers.
MATRIX: dict[str, dict[str, Expected]] = {
    "GET /me": ALL_OK,
    "GET /companies": ALL_OK,
    "POST /companies": {p: (201 if p == "admin" else 403) for p in PERSONAS},
    "PATCH /companies/{id}": ADMIN_ONLY,
    "POST /companies/{id}/archive": ADMIN_ONLY,
    "GET /companies/{id}/members": {**ALL_OK, "outsider": 404, "nobody": 404},
    "PUT /companies/{id}/members/{user_id}": ADMIN_ONLY,
    "GET /users": ADMIN_ONLY,
    "GET /users/{user_id}": ADMIN_ONLY,
    "POST /users": ADMIN_CREATES,
    "POST /users/{user_id}/reset-password": ADMIN_ONLY,
    "PATCH /users/{user_id}": ADMIN_ONLY,
    "GET /permissions/matrix": ANY_ROLE,
    # Global chain: app admin only (ADR 0006 §6) - 403 for everybody else.
    "POST /audit/verify": ADMIN_ONLY,
    "GET /audit": ADMIN_ONLY,
    # Company chain: auditor of the company; non-members 404 (§7.3). The admin verifies any
    # company chain on the admin path, but reads entries only with a membership (ADR 0009).
    "POST /audit/verify?company": {
        "admin": 200,
        "auditor": 200,
        "approver": 403,
        "editor": 403,
        "viewer": 403,
        "outsider": 404,
        "nobody": 404,
    },
    # The admin reads ANY company chain on the narrow read path (owner decision
    # 2026-11-02, ADR 0015 §7); everybody else needs the auditor role in the company.
    "GET /audit?company": {
        "admin": 200,
        "auditor": 200,
        "approver": 403,
        "editor": 403,
        "viewer": 403,
        "outsider": 404,
        "nobody": 404,
    },
    "GET /categories": ANY_ROLE,
    "POST /categories": ADMIN_CREATES,
    "PATCH /categories/{category_id}": ADMIN_ONLY,
    "GET /ci-types": ANY_ROLE,
    "POST /ci-types": ADMIN_CREATES,
    "PATCH /ci-types/{ci_type_id}": ADMIN_ONLY,
    "GET /companies/{id}/categories": COMPANY_READ,
    "PUT /companies/{id}/categories": ADMIN_ONLY,
    "GET /companies/{id}/ci": COMPANY_READ,
    "POST /companies/{id}/ci": {p: (201 if s == 200 else s) for p, s in CI_WRITE.items()},
    "GET /companies/{id}/ci/{ci_id}": COMPANY_READ,
    "PATCH /companies/{id}/ci/{ci_id}": CI_WRITE,
    "GET /companies/{id}/changes": REGISTER_READ,
    "POST /companies/{id}/changes": CHANGE_CREATE,
    "GET /companies/{id}/changes/by-number/{number}": REGISTER_READ,
    "GET /companies/{id}/changes/{change_id}": REGISTER_READ,
    "PATCH /companies/{id}/changes/{change_id}": CHANGE_WRITE,
    "GET /companies/{id}/changes/{change_id}/readiness": REGISTER_READ,
    "POST /companies/{id}/changes/{change_id}/actions/{action}?cancel": {
        **CHANGE_WRITE,
        "approver": (403, "change.forbidden_actor"),
    },
    "POST /companies/{id}/changes/{change_id}/actions/{action}?approve": {
        **CHANGE_WRITE,
        "editor": 403,
    },
    # submit: the author (editor); the approver passes the matrix, not the state machine
    "POST /companies/{id}/changes/{change_id}/actions/{action}?submit": {
        **CHANGE_WRITE,
        "approver": (403, "change.forbidden_actor"),
    },
    "POST /companies/{id}/changes/{change_id}/actions/{action}?reject": {
        **CHANGE_WRITE,
        "editor": 403,
    },
    "POST /companies/{id}/changes/{change_id}/actions/{action}?return": {
        **CHANGE_WRITE,
        "editor": 403,
    },
    # implement: the assignee (editor) only
    "POST /companies/{id}/changes/{change_id}/actions/{action}?implement": {
        **CHANGE_WRITE,
        "approver": (403, "change.forbidden_actor"),
    },
    # verify: not the assignee while another person can verify (§4.2)
    "POST /companies/{id}/changes/{change_id}/actions/{action}?verify": {
        **CHANGE_WRITE,
        "editor": (403, "change.verifier_is_assignee"),
    },
    # rollback: the assignee or the designated approver
    "POST /companies/{id}/changes/{change_id}/actions/{action}?rollback": CHANGE_WRITE,
    "POST /companies/{id}/changes/{change_id}/actions/{action}?consent": {
        **MEMBER_READ,
        "approver": NO_CONSENT_RULE,
        "editor": NO_CONSENT_RULE,
        "auditor": NO_CONSENT_RULE,
        "viewer": NO_CONSENT_RULE,
    },
    "GET /companies/{id}/changes/{change_id}/audit": REGISTER_READ,
    "POST /companies/{id}/changes/{change_id}/comments": CHANGE_CREATE,
    "GET /companies/{id}/changes/{change_id}/attachments": REGISTER_READ,
    "POST /companies/{id}/changes/{change_id}/attachments": CHANGE_CREATE,
    "GET /companies/{id}/changes/{change_id}/attachments/{attachment_id}": MEMBER_READ,
    "GET /companies/{id}/stats": REGISTER_READ,
    "GET /companies/{id}/audit/status": COMPANY_READ,
    # Stage 7 (§5 "Eksport PDF/CSV": admin, approver, auditor; editor - the change card
    # only; viewer nothing). The admin without a role: the named admin export path.
    "POST /reports?register": REPORT_CREATE,
    "POST /reports?change_card": {**REPORT_CREATE, "editor": 201},
    # Multi-company report: the auditor role (in every company of the report).
    "POST /reports?all": {p: (201 if p == "auditor" else 403) for p in PERSONAS},
    "GET /reports": {**ALL_OK, "viewer": 403, "nobody": 403},
    "GET /reports?company": {**COMPANY_READ, "viewer": 403},
    "GET /reports/{report_id}": REPORT_READ,
    "GET /reports/{report_id}/download": REPORT_READ,
    "GET /companies/{id}/changes/export.csv": EXPORT_REGISTER,
}

# endpoint -> who performs it in the audit test (default: the app admin)
MODIFYING_AS: dict[str, str] = {
    "POST /companies/{id}/changes": "editor",
    "PATCH /companies/{id}/changes/{change_id}": "editor",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?cancel": "editor",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?approve": "approver",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?submit": "editor",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?reject": "approver",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?return": "approver",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?implement": "editor",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?verify": "approver",
    "POST /companies/{id}/changes/{change_id}/actions/{action}?rollback": "editor",
    "POST /companies/{id}/changes/{change_id}/comments": "editor",
    "POST /companies/{id}/changes/{change_id}/attachments": "editor",
    "POST /reports?register": "auditor",
    "POST /reports?change_card": "editor",
    "POST /reports?all": "auditor",
}

MODIFYING = {
    *MODIFYING_AS,
    "POST /companies",
    "PATCH /companies/{id}",
    "POST /companies/{id}/archive",
    "PUT /companies/{id}/members/{user_id}",
    "POST /users",
    "POST /users/{user_id}/reset-password",
    "PATCH /users/{user_id}",
    # Writes only its own audit entry - the verification is an audited operation (§6.4).
    "POST /audit/verify",
    "POST /audit/verify?company",
    "POST /categories",
    "PATCH /categories/{category_id}",
    "POST /ci-types",
    "PATCH /ci-types/{ci_type_id}",
    "PUT /companies/{id}/categories",
    "POST /companies/{id}/ci",
    "PATCH /companies/{id}/ci/{ci_id}",
}


def test_matrix_covers_every_api_route() -> None:
    app = create_app(make_settings())
    routes = {
        f"{m} {r.path.removeprefix('/api/v1')}".replace("{company_id}", "{id}")
        for r in route_declarations(app)
        for m in r.methods
        if r.path not in PUBLIC_ENDPOINTS and r.path.startswith("/api/v1")
    }
    # "?variant" keys are the same route with different query parameters.
    assert routes == {key.split("?")[0] for key in MATRIX}
    assert set(MATRIX) == set(ENDPOINTS)


# Modifying routes that exist in one AUTH_MODE only (ADR 0018). Local accounts: every one
# writes audit entries - checked by
# test_local_auth.test_every_local_auth_endpoint_writes_audit_without_secrets (login,
# token_refresh, password_change, logout), which needs local tokens.
MODIFYING_BY_MODE: dict[str, set[str]] = {
    "local": {
        "POST /auth/login",
        "POST /auth/refresh",
        "POST /auth/logout",
        "POST /auth/password",
    },
    # Dev login: the token endpoint only signs a token; the "login" entry is written by
    # the first request with it (ADR 0010 §1). Never in production.
    "dev": {"POST /auth/dev/token"},
}


@pytest.mark.parametrize("auth_mode", ["dev", "local"])
def test_every_modifying_route_is_checked_for_audit(auth_mode: str) -> None:
    """Public routes included: login and refresh modify data (sessions) too."""
    app = create_app(
        make_settings(
            auth_mode=auth_mode,
            dev_auth_secret=None if auth_mode == "local" else make_settings().dev_auth_secret,
            auth_jwt_secret=LOCAL_SECRET,
        )
    )
    modifying_routes = {
        f"{m} {r.path.removeprefix('/api/v1')}".replace("{company_id}", "{id}")
        for r in route_declarations(app)
        for m in r.methods
        if m in {"POST", "PUT", "PATCH", "DELETE"} and r.path.startswith("/api/v1")
    }
    expected = {key.split("?")[0] for key in MODIFYING} | MODIFYING_BY_MODE[auth_mode]
    assert modifying_routes == expected


@pytest.mark.db
@pytest.mark.parametrize("endpoint", list(MATRIX))
@pytest.mark.parametrize("persona", PERSONAS)
async def test_permission_matrix(
    api: AsyncClient, world: World, endpoint: str, persona: str
) -> None:
    method, url, body = ENDPOINTS[endpoint](world)
    response = await api.request(method, url, **_send(body), headers=auth(world.persona(persona)))
    expected = MATRIX[endpoint][persona]
    if isinstance(expected, tuple):
        assert_problem(response, *expected)
        return
    assert response.status_code == expected, (endpoint, persona, response.text)
    if expected == 403:
        assert_problem(response, 403, "auth.forbidden")
    if expected == 404:
        assert_problem(response, 404, "company.not_found")


@pytest.mark.db
@pytest.mark.parametrize("endpoint", sorted(MODIFYING))
async def test_every_modifying_endpoint_writes_audit(
    api: AsyncClient, world: World, endpoint: str, rw_engine: Any
) -> None:
    """The endpoint itself wrote >= 1 entry in this request (login / auth events excluded)."""
    from sqlalchemy import text

    from tests.factories import scoped, verify

    method, url, body = ENDPOINTS[endpoint](world)
    who = world.persona(MODIFYING_AS.get(endpoint, "admin"))
    # Log in first, so the request under test cannot pass by its "login" entry alone.
    assert (await api.get("/api/v1/me", headers=auth(who))).status_code == 200
    response = await api.request(method, url, **_send(body), headers=auth(who))
    assert response.status_code in (200, 201), response.text
    async with scoped(rw_engine, [world.a.id], global_read=True) as session:
        written = (
            await session.execute(
                text(
                    "SELECT count(*) FROM audit_log WHERE request_id = :r AND entity_type <> 'auth'"
                ),
                {"r": response.headers["X-Request-ID"]},
            )
        ).scalar_one()
    assert written >= 1
    assert (await verify(rw_engine, None)).ok
    assert (await verify(rw_engine, world.a.id)).ok


# --------------------------------------------------------------------------- company context


@pytest.mark.db
async def test_company_context_requires_membership_even_for_admin(
    db_urls: DbUrls, world: World
) -> None:
    """Register context (no admin path): admin without membership gets 404 (§5, §7.3)."""
    app = create_app(make_settings(database_url=db_urls.rw))

    @app.get("/api/v1/_test/companies/{company_id}/register")
    async def _register(
        session: SessionDep, ctx: Any = require_company(Action.REGISTER_VIEW)
    ) -> dict[str, Any]:
        return {"company": str(ctx.company.id), "roles": sorted(ctx.roles)}

    @app.post("/api/v1/_test/companies/{company_id}/approve")
    async def _approve(ctx: Any = require_company(Action.CHANGE_APPROVE)) -> dict[str, str]:
        return {"ok": "yes"}

    url = f"/api/v1/_test/companies/{world.a.id}"
    try:
        async with client_for(app) as client:
            admin = await client.get(f"{url}/register", headers=auth(world.admin))
            viewer = await client.get(f"{url}/register", headers=auth(world.viewer))
            outsider = await client.get(f"{url}/register", headers=auth(world.outsider))
            viewer_approve = await client.post(f"{url}/approve", headers=auth(world.viewer))
            approver_approve = await client.post(f"{url}/approve", headers=auth(world.approver))
            missing = await client.get(
                f"/api/v1/_test/companies/{UUID(int=1)}/register", headers=auth(world.viewer)
            )
    finally:
        await app.state.db.dispose()
    assert_problem(admin, 404, "company.not_found")
    assert viewer.json() == {"company": str(world.a.id), "roles": ["viewer"]}
    assert_problem(outsider, 404, "company.not_found")
    assert_problem(viewer_approve, 403, "auth.forbidden")
    assert approver_approve.status_code == 200
    assert_problem(missing, 404, "company.not_found")
