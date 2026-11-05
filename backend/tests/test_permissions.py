"""Skeleton checks of the RBAC source of truth (full matrix tests arrive with endpoints)."""

from collections.abc import Callable
from typing import Any

import pytest

from app.permissions import (
    PERMISSIONS,
    READ_ACTIONS,
    Action,
    Role,
    is_allowed,
    require_company,
    route_declarations,
    visible_companies,
)


def test_every_action_has_an_entry() -> None:
    assert set(PERMISSIONS) == set(Action)


def test_app_admin_is_not_implicitly_editor_or_approver() -> None:
    assert not is_allowed(Role.APP_ADMIN, Action.CHANGE_EDIT_DRAFT)
    assert not is_allowed(Role.APP_ADMIN, Action.CHANGE_APPROVE)


def test_viewer_can_only_read() -> None:
    allowed = {a for a in Action if is_allowed(Role.VIEWER, a)}
    assert allowed == {Action.REGISTER_VIEW}


def test_audit_verify_only_admin_and_auditor() -> None:
    allowed = {r for r in Role if is_allowed(r, Action.AUDIT_VERIFY)}
    assert allowed == {Role.APP_ADMIN, Role.AUDITOR}


def test_editor_exports_only_change_card() -> None:
    assert is_allowed(Role.EDITOR, Action.EXPORT_CHANGE_CARD)
    assert not is_allowed(Role.EDITOR, Action.EXPORT_REGISTER)
    assert not is_allowed(Role.VIEWER, Action.EXPORT_CHANGE_CARD)


# --------------------------------------------------------------------------- admin_action
# The administrative path of require_company / visible_companies skips the check of the
# endpoint's own action, so it is only allowed on read endpoints, or when the admin action
# IS the endpoint's action and app_admin holds it in the matrix (CI inventory, §5) - fail
# fast on declaration otherwise.

_WRITE_ACTIONS = sorted(set(Action) - READ_ACTIONS)


def test_read_actions_are_reads_only() -> None:
    assert frozenset({Action.REGISTER_VIEW}) == READ_ACTIONS


@pytest.mark.parametrize("action", _WRITE_ACTIONS)
@pytest.mark.parametrize("declare", [require_company, visible_companies])
def test_admin_action_on_write_endpoint_fails_at_declaration(
    declare: Callable[..., Any], action: Action
) -> None:
    other = Action.COMPANY_MANAGE if action != Action.COMPANY_MANAGE else Action.CI_MANAGE
    with pytest.raises(ValueError, match="admin_action"):
        declare(action, admin_action=other)


@pytest.mark.parametrize("declare", [require_company, visible_companies])
def test_admin_action_must_be_an_app_admin_action(declare: Callable[..., Any]) -> None:
    with pytest.raises(ValueError, match="admin_action"):
        declare(Action.REGISTER_VIEW, admin_action=Action.CHANGE_APPROVE)


@pytest.mark.parametrize("declare", [require_company, visible_companies])
def test_admin_action_allowed_on_read_endpoint(declare: Callable[..., Any]) -> None:
    declare(Action.REGISTER_VIEW, admin_action=Action.MEMBERSHIP_MANAGE)
    for action in Action:
        declare(action)  # without admin_action every action can be declared


@pytest.mark.parametrize("action", [a for a in _WRITE_ACTIONS if is_allowed(Role.APP_ADMIN, a)])
def test_admin_action_equal_to_an_admin_write_action_is_allowed(action: Action) -> None:
    """The admin path checks the very same action (e.g. ``ci.manage``): nothing is skipped."""
    require_company(action, admin_action=action)


@pytest.mark.parametrize("action", [a for a in _WRITE_ACTIONS if not is_allowed(Role.APP_ADMIN, a)])
def test_admin_action_equal_to_a_non_admin_action_fails(action: Action) -> None:
    """E.g. ``change.approve``: the admin does not hold it, so no admin path (SoD, §5)."""
    with pytest.raises(ValueError, match="admin_action"):
        require_company(action, admin_action=action)


def test_declared_routes_respect_the_rule() -> None:
    from app.main import create_app
    from tests.conftest import make_settings

    for route in route_declarations(create_app(make_settings())):
        for rule in route.rules:
            if rule.admin_action is not None:
                assert rule.action in READ_ACTIONS or (
                    rule.admin_action == rule.action and is_allowed(Role.APP_ADMIN, rule.action)
                ), route.path


def test_require_in_any_company_declares_its_kind() -> None:
    from app.permissions import AccessRule, require_in_any_company

    dependency = require_in_any_company(Action.REGISTER_VIEW)
    rule = dependency.dependency.__access_rule__
    assert rule == AccessRule(Action.REGISTER_VIEW, "any_company")


def test_every_change_action_has_a_matrix_row() -> None:
    """``POST .../actions/{action}``: each state machine action maps to a §5 row; approving
    is the approver's, the rest of the workflow the writers' (editor, approver), and the
    CI owner's consent is open to any role (ADR 0012 §5, ADR 0013 §7)."""
    from app.domain.changes import ChangeAction
    from app.permissions import CHANGE_ACTION_PERMISSIONS, PERMISSIONS, Role

    assert set(CHANGE_ACTION_PERMISSIONS) == {a.value for a in ChangeAction}
    for name in ("approve", "reject", "return"):
        assert CHANGE_ACTION_PERMISSIONS[name] is Action.CHANGE_APPROVE
    for name in ("submit", "cancel", "implement", "verify", "rollback"):
        assert CHANGE_ACTION_PERMISSIONS[name] is Action.CHANGE_EDIT_DRAFT
    assert CHANGE_ACTION_PERMISSIONS["consent"] is Action.REGISTER_VIEW
    # The app admin performs no change action (segregation of duties, §5).
    for name, action in CHANGE_ACTION_PERMISSIONS.items():
        if name != "consent":
            assert Role.APP_ADMIN not in PERMISSIONS[action], name


def test_change_routes_admin_path_only_read_only_reads() -> None:
    """Writes, actions and the attachment download: no admin path (ADR 0013 §7). The
    register reads: only the named narrow READ-ONLY admin path (ADR 0016)."""
    from app.main import create_app
    from app.permissions import CHANGE_ACTION_PERMISSIONS, route_declarations
    from tests.conftest import make_settings

    all_routes = route_declarations(create_app(make_settings()))
    # The CSV export (stage 7) is an EXPORT, not a register read: export.register with the
    # named admin export path (admin_action == action, ADR 0017 §4) - checked separately.
    (csv,) = [r for r in all_routes if r.path.endswith("/changes/export.csv")]
    (csv_rule,) = csv.rules
    assert csv_rule.action == csv_rule.admin_action == Action.EXPORT_REGISTER
    assert not csv_rule.admin_read_only
    routes = [
        r
        for r in all_routes
        if ("/changes" in r.path or r.path.endswith("/stats")) and r is not csv
    ]
    assert len(routes) == 13
    admin_reads = set()
    for route in routes:
        (rule,) = route.rules
        assert rule.kind == "company"
        download = route.path.endswith("/attachments/{attachment_id}")
        if route.methods == {"GET"} and not download:
            assert rule.action == Action.REGISTER_VIEW, route.path
            assert rule.admin_action == Action.REGISTER_VIEW, route.path
            assert rule.admin_read_only, route.path
            admin_reads.add(route.path.removeprefix("/api/v1/companies/{company_id}"))
        else:
            assert rule.admin_action is None, route.path
            assert not rule.admin_read_only, route.path
        if route.path.endswith("/actions/{action}"):
            assert dict(rule.per_value) == dict(CHANGE_ACTION_PERMISSIONS)
    assert admin_reads == {
        "/changes",
        "/changes/by-number/{number}",
        "/changes/{change_id}",
        "/changes/{change_id}/readiness",
        "/changes/{change_id}/audit",
        "/changes/{change_id}/attachments",
        "/stats",
    }


def test_admin_read_only_requires_a_read_action() -> None:
    from app.permissions import require_company

    with pytest.raises(ValueError, match="admin_read_only"):
        require_company(Action.REGISTER_VIEW, admin_read_only=True)
    with pytest.raises(ValueError, match="admin_action"):
        require_company(Action.CI_MANAGE, admin_action=Action.CI_MANAGE, admin_read_only=True)
