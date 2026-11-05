"""``GET /permissions/matrix`` — the RBAC matrix of ``app.permissions`` (read-only, ADR 0015).

The UI renders the matrix from this response instead of duplicating it (CLAUDE.md §5,
§10.4). Readable by anybody with a role in any company and by the app admin
(``require_in_any_company``, like the shared dictionaries): the matrix is configuration of
the application, not data of a company. Static data - no audit entry.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.auth.principal import CurrentUser
from app.permissions import (
    ACTION_DESCRIPTIONS,
    CHANGE_ACTION_PERMISSIONS,
    PERMISSIONS,
    Action,
    Role,
    require_in_any_company,
)
from app.schemas.permissions import ChangeActionRuleOut, MatrixRowOut, PermissionMatrixOut

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/matrix", response_model=PermissionMatrixOut)
async def permission_matrix(
    _: CurrentUser = require_in_any_company(Action.REGISTER_VIEW),
) -> PermissionMatrixOut:
    roles = list(Role)  # column order of CLAUDE.md §5
    return PermissionMatrixOut(
        roles=[r.value for r in roles],
        actions=[
            MatrixRowOut(
                action=action.value,
                label=ACTION_DESCRIPTIONS[action][0],
                note=ACTION_DESCRIPTIONS[action][1],
                roles=[r.value for r in roles if r in PERMISSIONS[action]],
            )
            for action in Action
        ],
        change_actions=[
            ChangeActionRuleOut(action=name, requires=required.value)
            for name, required in CHANGE_ACTION_PERMISSIONS.items()
        ],
    )
