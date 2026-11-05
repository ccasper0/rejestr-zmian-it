"""Roles (CLAUDE.md §5). Pure Python, no I/O.

Defined in the domain so that domain rules (``app.domain.state_machine``) can reason about
roles without importing the FastAPI layer. ``app.permissions`` re-exports these names and
stays the single source of truth for the action matrix.
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    # Global flag users.is_app_admin - NOT a company membership role and never implies
    # editor/approver rights (segregation of duties).
    APP_ADMIN = "app_admin"
    # company_memberships.role
    APPROVER = "approver"
    EDITOR = "editor"
    AUDITOR = "auditor"
    VIEWER = "viewer"


MEMBERSHIP_ROLES: frozenset[Role] = frozenset(Role) - {Role.APP_ADMIN}
