"""``CurrentUser`` / ``CompanyContext``: scope, global audit read path, audit actor."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.auth.principal import CurrentUser
from app.permissions import Role

A = UUID("00000000-0000-4000-8000-00000000000a")
B = UUID("00000000-0000-4000-8000-00000000000b")


def principal(*, admin: bool = False, **memberships: frozenset[Role]) -> CurrentUser:
    by_company = {A: memberships.get("a", frozenset()), B: memberships.get("b", frozenset())}
    return CurrentUser(
        id=uuid4(),
        external_id="sub",
        email="x@example.com",
        display_name="Jan Kowalski",
        is_app_admin=admin,
        memberships={cid: roles for cid, roles in by_company.items() if roles},
    )


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        pytest.param(principal(), False, id="no-roles"),
        pytest.param(principal(a=frozenset({Role.VIEWER})), False, id="viewer"),
        pytest.param(principal(a=frozenset({Role.EDITOR})), False, id="editor"),
        pytest.param(principal(a=frozenset({Role.APPROVER})), False, id="approver"),
        pytest.param(principal(a=frozenset({Role.AUDITOR})), False, id="auditor"),
        pytest.param(
            principal(a=frozenset({Role.AUDITOR}), b=frozenset({Role.AUDITOR})),
            False,
            id="auditor-of-every-company",
        ),
        pytest.param(principal(admin=True), True, id="app-admin"),
        pytest.param(
            principal(admin=True, a=frozenset({Role.AUDITOR})), True, id="admin-and-auditor"
        ),
    ],
)
def test_global_audit_read_is_for_app_admins_only(user: CurrentUser, expected: bool) -> None:
    """The global chain holds data of every company (ADR 0006 §6): auditors read only
    the chains of their companies."""
    assert user.global_audit_read is expected


def test_company_ids_are_companies_with_roles_sorted() -> None:
    user = principal(b=frozenset({Role.VIEWER}), a=frozenset({Role.AUDITOR}))
    assert user.company_ids == (A, B)
    assert principal().company_ids == ()


def test_global_roles_and_roles_in() -> None:
    admin = principal(admin=True, a=frozenset({Role.EDITOR}))
    assert admin.global_roles == frozenset({Role.APP_ADMIN})
    assert admin.roles_in(A) == frozenset({Role.EDITOR})
    assert admin.roles_in(B) == frozenset()
    assert principal().global_roles == frozenset()


def test_actor_freezes_global_and_company_roles() -> None:
    admin = principal(admin=True, a=frozenset({Role.EDITOR, Role.APPROVER}))
    assert admin.actor().roles == ("app_admin",)
    assert admin.actor(A).roles == ("app_admin", "approver", "editor")
    assert admin.actor(B).roles == ("app_admin",)
    assert admin.actor(A).display == "Jan Kowalski"
    assert admin.actor(A).id == admin.id
