"""``GET /permissions/matrix`` (ADR 0015)."""

from __future__ import annotations

from pydantic import BaseModel


class MatrixRowOut(BaseModel):
    action: str
    label: str
    note: str | None
    # Roles holding the action, in the column order of ``PermissionMatrixOut.roles``.
    roles: list[str]


class ChangeActionRuleOut(BaseModel):
    """``POST .../actions/{action}``: the matrix action it requires (then the state machine)."""

    action: str
    requires: str


class PermissionMatrixOut(BaseModel):
    roles: list[str]
    actions: list[MatrixRowOut]
    change_actions: list[ChangeActionRuleOut]
