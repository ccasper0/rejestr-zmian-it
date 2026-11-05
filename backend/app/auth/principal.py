"""The authenticated user of a request, with roles per company (CLAUDE.md 5)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.audit import Actor
from app.models import Company, ReportExport
from app.permissions import Role


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    external_id: str
    email: str
    display_name: str
    is_app_admin: bool
    # company_id -> membership roles (never contains Role.APP_ADMIN)
    memberships: Mapping[UUID, frozenset[Role]] = field(default_factory=dict)
    # Local accounts (ADR 0018): the server-side session of the access token, and whether
    # the password must be changed before anything else is allowed. Dev mode: None/False.
    session_id: UUID | None = None
    must_change_password: bool = False

    @property
    def company_ids(self) -> tuple[UUID, ...]:
        """Companies with at least one membership role (the RLS scope of the request)."""
        return tuple(sorted(cid for cid, roles in self.memberships.items() if roles))

    @property
    def global_roles(self) -> frozenset[Role]:
        """Roles not bound to a company: only ``app_admin`` (``users.is_app_admin``)."""
        return frozenset({Role.APP_ADMIN}) if self.is_app_admin else frozenset()

    @property
    def global_audit_read(self) -> bool:
        """Explicit read path of the global audit chain: app admins ONLY (ADR 0006 §6).

        The global chain holds data of every company (company names, NIP, user e-mails,
        access denials with ``target_company_id``), so a company auditor must not read
        it (CLAUDE.md §1.2, §7). Auditors verify the chains of their companies; the
        global chain is read and verified by app admins. A per-company view of global
        events (``subject_company_id``) is a possible extension (ADR 0008 §6).
        """
        return self.is_app_admin

    def roles_in(self, company_id: UUID) -> frozenset[Role]:
        """Membership roles in the company (``app_admin`` is NOT included, see §5)."""
        return self.memberships.get(company_id, frozenset())

    def actor(self, company_id: UUID | None = None) -> Actor:
        """Audit actor; roles frozen into the entry: global roles + roles in ``company_id``."""
        roles = set(self.global_roles)
        if company_id is not None:
            roles |= self.roles_in(company_id)
        return Actor(id=self.id, display=self.display_name, roles=tuple(r.value for r in roles))


@dataclass(frozen=True, slots=True)
class CompanyContext:
    """A company resolved for the current request (``get_company_context``).

    ``roles``: membership roles in the company plus ``app_admin`` for app admins.
    ``admin_path``: resolved through the explicit administrative path (app admin, possibly
    without membership — only on administrative endpoints, CLAUDE.md §5 / §7 pt 2).
    ``read_only``: the narrow administrative READ path (app admin without membership, READ
    ONLY transaction; ADR 0015 §7, ADR 0016) - the caller may only read.
    """

    company: Company
    user: CurrentUser
    roles: frozenset[Role]
    admin_path: bool = False
    read_only: bool = False

    @property
    def company_id(self) -> UUID:
        return self.company.id

    def actor(self) -> Actor:
        return Actor(
            id=self.user.id,
            display=self.user.display_name,
            roles=tuple(r.value for r in self.roles),
        )


@dataclass(frozen=True, slots=True)
class AuditChainContext:
    """One audit chain resolved for the current request (``require_audit_chain``).

    ``company`` is ``None`` for the global chain (app admins only, ADR 0006 §6).
    ``roles``: roles in the company plus ``app_admin`` (global chain: ``app_admin`` only).
    ``admin_path``: an app admin reached a company chain without membership through the
    explicit administrative path (chain verification only, ADR 0009).
    """

    user: CurrentUser
    company: Company | None
    roles: frozenset[Role]
    admin_path: bool = False

    @property
    def company_id(self) -> UUID | None:
        return None if self.company is None else self.company.id

    def actor(self) -> Actor:
        return Actor(
            id=self.user.id,
            display=self.user.display_name,
            roles=tuple(r.value for r in self.roles),
        )


@dataclass(frozen=True, slots=True)
class ReportOrder:
    """``POST /reports`` after the permission check (``require_report_order``, ADR 0017).

    ``company`` is ``None`` for the multi-company report of an auditor; ``companies`` are
    the companies of the report (all in the transaction scope). ``admin_path``: an app
    admin without a role in the company, on the named admin export path. ``body``: the
    request (``app.schemas.reports.ReportCreate``).
    """

    user: CurrentUser
    company: Company | None
    companies: tuple[Company, ...]
    body: Any
    admin_path: bool = False


@dataclass(frozen=True, slots=True)
class ReportListing:
    """``GET /reports``: which rows the user may list (``require_report_list``)."""

    user: CurrentUser
    company_id: UUID | None
    all_rows: bool
    register_company_ids: frozenset[UUID]
    card_company_ids: frozenset[UUID]


@dataclass(frozen=True, slots=True)
class ReportAccess:
    """One report (``GET /reports/{id}``, ``.../download``) the user may access."""

    user: CurrentUser
    report: ReportExport
    admin_path: bool = False
