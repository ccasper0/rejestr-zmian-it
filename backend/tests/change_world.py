"""A small, fixed world for the pure change-domain tests (no database)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.domain.changes import (
    ActorFacts,
    CategoryFacts,
    ChangeContext,
    ChangeData,
    ChangeStatus,
    ChangeType,
    CIFacts,
    CompanyFacts,
    MemberFacts,
    Risk,
)
from app.domain.roles import Role

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)

COMPANY_ID = uuid4()
OTHER_COMPANY_ID = uuid4()

# users (their roles in the company are in ROLES)
AUTHOR = uuid4()  # requested_by
ASSIGNEE = uuid4()
APPROVER = uuid4()  # designated approver_id
APPROVER2 = uuid4()  # another approver of the company (not designated)
VERIFIER = uuid4()  # designated verifier_id
EDITOR2 = uuid4()  # unrelated editor
VIEWER = uuid4()
AUDITOR = uuid4()
OWNER = uuid4()  # owner of CI_OT (viewer)
OUTSIDER = uuid4()  # no membership (e.g. app_admin without a company role)
INACTIVE_APPROVER = uuid4()

ROLES: dict[UUID, frozenset[Role]] = {
    AUTHOR: frozenset({Role.EDITOR}),
    ASSIGNEE: frozenset({Role.EDITOR}),
    APPROVER: frozenset({Role.APPROVER}),
    APPROVER2: frozenset({Role.APPROVER, Role.EDITOR}),
    VERIFIER: frozenset({Role.EDITOR}),
    EDITOR2: frozenset({Role.EDITOR}),
    VIEWER: frozenset({Role.VIEWER}),
    AUDITOR: frozenset({Role.AUDITOR}),
    OWNER: frozenset({Role.VIEWER}),
    INACTIVE_APPROVER: frozenset({Role.APPROVER}),
}

ACTORS: dict[str, UUID] = {
    "author": AUTHOR,
    "assignee": ASSIGNEE,
    "approver": APPROVER,
    "approver2": APPROVER2,
    "verifier": VERIFIER,
    "editor2": EDITOR2,
    "viewer": VIEWER,
    "auditor": AUDITOR,
    "owner": OWNER,
    "outsider": OUTSIDER,
}


def actor(user_id: UUID, roles: frozenset[Role] | None = None) -> ActorFacts:
    return ActorFacts(user_id, ROLES.get(user_id, frozenset()) if roles is None else roles)


MEMBERS: dict[UUID, MemberFacts] = {
    uid: MemberFacts(is_active=uid != INACTIVE_APPROVER, roles=roles)
    for uid, roles in ROLES.items()
}

# categories
NET = uuid4()  # requires approval
ACC = uuid4()  # standard, no approval
ACC_PRIV = uuid4()  # subcategory of ACC requiring approval
ACC_GRANT = uuid4()  # subcategory of ACC without approval
OT = uuid4()  # approval + CI owner consent
ACC_OT = uuid4()  # subcategory of ACC requiring consent only
INACTIVE_CAT = uuid4()
UNAVAILABLE_CAT = uuid4()
NET_VLAN_INACTIVE = uuid4()

CATEGORIES: dict[UUID, CategoryFacts] = {
    NET: CategoryFacts(NET, None, True, True, available_in_company=True),
    ACC: CategoryFacts(ACC, None, True, False, available_in_company=True),
    ACC_PRIV: CategoryFacts(ACC_PRIV, ACC, True, True),
    ACC_GRANT: CategoryFacts(ACC_GRANT, ACC, True, False),
    ACC_OT: CategoryFacts(ACC_OT, ACC, True, False, requires_ci_owner_consent=True),
    OT: CategoryFacts(
        OT, None, True, True, requires_ci_owner_consent=True, available_in_company=True
    ),
    INACTIVE_CAT: CategoryFacts(INACTIVE_CAT, None, False, True, available_in_company=True),
    UNAVAILABLE_CAT: CategoryFacts(UNAVAILABLE_CAT, None, True, True),
    NET_VLAN_INACTIVE: CategoryFacts(NET_VLAN_INACTIVE, NET, False, True),
}

# configuration items
CI_FW = uuid4()
CI_OT = uuid4()  # owned by OWNER
CI_OT2 = uuid4()  # owned by OWNER as well
CI_SRV = uuid4()  # owned by EDITOR2
CI_NO_OWNER = uuid4()
CI_INACTIVE = uuid4()
CI_FOREIGN = uuid4()  # another company (normally hidden by RLS)

CIS: dict[UUID, CIFacts] = {
    CI_FW: CIFacts(CI_FW, COMPANY_ID, True, "FW-01"),
    CI_OT: CIFacts(CI_OT, COMPANY_ID, True, "PLC-01", owner_user_id=OWNER),
    CI_OT2: CIFacts(CI_OT2, COMPANY_ID, True, "PLC-02", owner_user_id=OWNER),
    CI_SRV: CIFacts(CI_SRV, COMPANY_ID, True, "SRV-01", owner_user_id=EDITOR2),
    CI_NO_OWNER: CIFacts(CI_NO_OWNER, COMPANY_ID, True, "HMI-01"),
    CI_INACTIVE: CIFacts(CI_INACTIVE, COMPANY_ID, False, "OLD-01"),
    CI_FOREIGN: CIFacts(CI_FOREIGN, OTHER_COMPANY_ID, True, "FW-99"),
}


def context(**overrides: Any) -> ChangeContext:
    base = ChangeContext(
        company=CompanyFacts(COMPANY_ID),
        categories=CATEGORIES,
        cis=CIS,
        members=MEMBERS,
    )
    return replace(base, **overrides)


def ready_change(**overrides: Any) -> ChangeData:
    """A normal, medium-risk draft that passes readiness at ``NOW``."""
    base = ChangeData(
        id=uuid4(),
        company_id=COMPANY_ID,
        status=ChangeStatus.DRAFT,
        requested_by_id=AUTHOR,
        title="Nowa reguła na FW-01",
        category_id=NET,
        change_type=ChangeType.NORMAL,
        risk=Risk.MEDIUM,
        description="Otwarcie portu 443 dla nowego serwera.",
        implementation_plan="1. Dodaj regułę. 2. Zapisz konfigurację.",
        assignee_id=ASSIGNEE,
        approver_id=APPROVER,
        verifier_id=VERIFIER,
        window_start=NOW + timedelta(days=1),
        window_end=NOW + timedelta(days=1, hours=2),
        ci_ids=frozenset({CI_FW}),
    )
    return replace(base, **overrides)


def in_status(status: ChangeStatus, **overrides: Any) -> ChangeData:
    """``ready_change`` moved to ``status`` with consistent timestamps."""
    stamps: dict[str, Any] = {}
    if status in {ChangeStatus.APPROVED, ChangeStatus.IMPLEMENTED, ChangeStatus.VERIFIED,
                  ChangeStatus.ROLLED_BACK}:  # fmt: skip
        stamps["approved_at"] = NOW - timedelta(days=3)
        stamps["approved_by_id"] = APPROVER
    if status in {ChangeStatus.IMPLEMENTED, ChangeStatus.VERIFIED, ChangeStatus.ROLLED_BACK}:
        stamps["implemented_at"] = NOW - timedelta(days=2)
        # implemented inside its (past) window - no implemented_outside_window deviation
        stamps["window_start"] = NOW - timedelta(days=2, hours=1)
        stamps["window_end"] = NOW - timedelta(days=2) + timedelta(hours=1)
    if status is ChangeStatus.VERIFIED:
        stamps["verified_at"] = NOW - timedelta(days=1)
    if status is ChangeStatus.REJECTED:
        stamps["rejected_at"] = NOW - timedelta(days=1)
    stamps.update(overrides)
    return ready_change(status=status, **stamps)
