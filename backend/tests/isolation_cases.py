"""THE list of API endpoints scoped to a company (CLAUDE.md §7.3) - extend it, never fork it.

Every route whose path contains ``{company_id}`` MUST have exactly one case here
(``tests/test_isolation_api.py`` fails otherwise). Routes that address a company-owned
resource without ``{company_id}`` in the path (e.g. ``/reports/{id}``) must be added too,
with ``foreign_resource``.

Kinds of access (ADR 0007 §4):

- ``member``: membership-based (register, cards, CI, ...). A user without membership in
  the company gets **404** ``company.not_found`` - identical to a non-existent company,
  so existence is not revealed. ``admin_path=True`` only if the route declares an
  ``admin_action`` the app admin has (then the admin needs no membership); otherwise the
  admin without membership gets 404 like everyone else (§5: admin is not a member).
- ``admin``: administrative only (edit/archive company, roles). Non-admins get **403**
  for every company, existing or not (the answer does not depend on the resource).

``foreign_resource`` (for routes with a resource id besides the company, e.g.
``/companies/{company_id}/changes/{change_id}``): creates a resource in the given company
and returns its path parameters. The test then asks for that resource under the caller's
OWN company path and expects 404 (swapping ids across companies must not work).

``params`` receives the TARGET company: a resource route addresses that company's own
resource (e.g. ``/companies/B/ci/{CI of B}``), so a 404 for a foreign company is about the
company, not about a mismatched resource. ``ok_personas``: the members of company A for
which the endpoint succeeds (write endpoints: only roles with the action).

``QUERY_CASES``: routes that take the company as the QUERY parameter ``company_id``
(audit chains, ADR 0009). Every route with such a parameter MUST be listed there; a user
without membership in that company gets the same 404 as for a non-existent company.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from app.models import Company
from app.permissions import Role
from tests.factories import World, make_attachment, make_change, make_ci, random_prefix

Access = Literal["member", "admin"]
Body = Callable[[World], dict[str, Any] | None]
Files = Callable[[World], dict[str, Any] | None]
Params = Callable[[World, UUID], dict[str, str]]
ForeignResource = Callable[[AsyncEngine, World, Company], Awaitable[dict[str, str]]]


def _no_body(_: World) -> dict[str, Any] | None:
    return None


def _no_params(_: World, __: UUID) -> dict[str, str]:
    return {}


def _no_files(_: World) -> dict[str, Any] | None:
    return None


A_MEMBERS = ("approver", "editor", "auditor", "viewer")
CI_MANAGERS = ("approver", "editor")


@dataclass(frozen=True)
class IsolationCase:
    method: str
    path: str  # the route path exactly as declared (with ``{company_id}``)
    access: Access
    admin_path: bool = False
    body: Body = _no_body
    params: Params = _no_params  # path parameters other than company_id
    foreign_resource: ForeignResource | None = None
    ok_personas: tuple[str, ...] = A_MEMBERS
    files: Files = _no_files  # multipart body instead of JSON (attachments)
    # A value of a resource parameter that exists nowhere (default: a random UUID).
    missing_value: Callable[[str], str] = lambda _name: str(uuid4())

    def send(self, world: World) -> dict[str, Any]:
        files = self.files(world)
        return {"files": files} if files is not None else {"json": self.body(world)}

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"

    def url(self, world: World, company_id: UUID, **extra: str) -> str:
        params = self.params(world, company_id)
        return self.path.format(company_id=company_id, **{**params, **extra})


CASES: tuple[IsolationCase, ...] = (
    IsolationCase(
        "PATCH",
        "/api/v1/companies/{company_id}",
        "admin",
        body=lambda w: {"is_ksc_entity": True},
    ),
    IsolationCase("POST", "/api/v1/companies/{company_id}/archive", "admin"),
    IsolationCase("GET", "/api/v1/companies/{company_id}/members", "member", admin_path=True),
    IsolationCase(
        "PUT",
        "/api/v1/companies/{company_id}/members/{user_id}",
        "admin",
        body=lambda w: {"roles": ["viewer"]},
        params=lambda w, _: {"user_id": str(w.nobody.id)},
    ),
    # Stage 3 (ADR 0011)
    IsolationCase("GET", "/api/v1/companies/{company_id}/categories", "member", admin_path=True),
    IsolationCase(
        "PUT",
        "/api/v1/companies/{company_id}/categories",
        "admin",
        body=lambda w: {"categories": [{"category_id": str(w.category.id)}]},
    ),
    IsolationCase("GET", "/api/v1/companies/{company_id}/ci", "member", admin_path=True),
    IsolationCase(
        "POST",
        "/api/v1/companies/{company_id}/ci",
        "member",
        admin_path=True,
        body=lambda w: {
            "ci_type_id": str(w.ci_type.id),
            "identifier": f"ISO-{random_prefix()}",
            "name": "Izolacja",
        },
        ok_personas=CI_MANAGERS,
    ),
    IsolationCase(
        "GET",
        "/api/v1/companies/{company_id}/ci/{ci_id}",
        "member",
        admin_path=True,
        params=lambda w, cid: {"ci_id": str(_own_ci(w, cid))},
        foreign_resource=lambda engine, w, company: _foreign_ci(engine, w, company),
    ),
    IsolationCase(
        "PATCH",
        "/api/v1/companies/{company_id}/ci/{ci_id}",
        "member",
        admin_path=True,
        body=lambda w: {"name": f"Izolacja {random_prefix()}"},
        params=lambda w, cid: {"ci_id": str(_own_ci(w, cid))},
        foreign_resource=lambda engine, w, company: _foreign_ci(engine, w, company),
        ok_personas=CI_MANAGERS,
    ),
)


CHANGES = "/api/v1/companies/{company_id}/changes"
CHANGE = CHANGES + "/{change_id}"
CHANGE_WRITERS = ("approver", "editor")


def _change_case(method: str, suffix: str = "", **kwargs: Any) -> IsolationCase:
    return IsolationCase(
        method,
        CHANGE + suffix,
        "member",
        params=lambda w, cid: {"change_id": str(_own_change(w, cid))},
        foreign_resource=lambda engine, w, company: _foreign_change(engine, w, company),
        **kwargs,
    )


# Stage 4 (ADR 0013): the admin without a role is not a member (§5) - no admin path for
# writes, actions and the attachment download; the register READS have the named narrow
# read-only admin path (owner decision 2026-11-02, ADR 0016).
CASES = (
    *CASES,
    IsolationCase("GET", CHANGES, "member", admin_path=True),
    IsolationCase(
        "POST", CHANGES, "member", body=lambda w: {"title": "Izolacja"}, ok_personas=CHANGE_WRITERS
    ),
    IsolationCase(
        "GET",
        CHANGES + "/by-number/{number}",
        "member",
        params=lambda w, cid: {"number": _own_number(w, cid)},
        foreign_resource=lambda engine, w, company: _foreign_number(engine, w, company),
        missing_value=lambda _name: f"CHG-{random_prefix()}-2026-9999",
        admin_path=True,
    ),
    _change_case("GET", admin_path=True),
    # A no-op edit (same title): succeeds for every writer, the version stays.
    _change_case(
        "PATCH",
        body=lambda w: {"title": w.draft_a.title if w.draft_a else None, "version": 1},
        ok_personas=CHANGE_WRITERS,
    ),
    _change_case("GET", "/readiness", admin_path=True),
    IsolationCase(
        "POST",
        CHANGE + "/actions/{action}",
        "member",
        params=lambda w, cid: {"change_id": str(_own_change(w, cid)), "action": "cancel"},
        foreign_resource=lambda engine, w, company: _foreign_change(engine, w, company),
        ok_personas=("editor",),  # the author
    ),
    _change_case("GET", "/audit", admin_path=True),
    _change_case(
        "POST", "/comments", body=lambda w: {"body": "Izolacja"}, ok_personas=CHANGE_WRITERS
    ),
    _change_case("GET", "/attachments", admin_path=True),
    _change_case(
        "POST",
        "/attachments",
        files=lambda w: {"file": ("izolacja.txt", b"izolacja", "text/plain")},
        ok_personas=CHANGE_WRITERS,
    ),
    IsolationCase(
        "GET",
        CHANGE + "/attachments/{attachment_id}",
        "member",
        params=lambda w, cid: _own_attachment(w, cid),
        foreign_resource=lambda engine, w, company: _foreign_attachment(engine, w, company),
    ),
    IsolationCase("GET", "/api/v1/companies/{company_id}/stats", "member", admin_path=True),
    IsolationCase("GET", "/api/v1/companies/{company_id}/audit/status", "member", admin_path=True),
    # Stage 7 (ADR 0017): CSV export - export.register; the app admin on the named admin
    # export path (writes report_exports + the audit entry of the company).
    IsolationCase(
        "GET",
        CHANGES + "/export.csv",
        "member",
        admin_path=True,
        ok_personas=("approver", "auditor"),
    ),
)


def _own_change(world: World, company_id: UUID) -> UUID:
    change = world.draft_b if company_id == world.b.id else world.draft_a
    assert change is not None, "the isolation tests need tests.factories.add_changes"
    return change.id


def _own_number(world: World, company_id: UUID) -> str:
    change = world.draft_b if company_id == world.b.id else world.draft_a
    assert change is not None
    return change.number


def _own_attachment(world: World, company_id: UUID) -> dict[str, str]:
    assert world.attachment_a is not None
    assert world.draft_a is not None
    # B has no attachment fixture: its change with A's attachment id (404 comes first anyway).
    return {
        "change_id": str(_own_change(world, company_id)),
        "attachment_id": str(world.attachment_a.id),
    }


async def _foreign_change(engine: AsyncEngine, world: World, company: Company) -> dict[str, str]:
    change = await make_change(engine, company, world.outsider, Role.EDITOR, Role.APPROVER)
    return {"change_id": str(change.id)}


async def _foreign_number(engine: AsyncEngine, world: World, company: Company) -> dict[str, str]:
    change = await make_change(engine, company, world.outsider, Role.EDITOR, Role.APPROVER)
    return {"number": change.number}


async def _foreign_attachment(
    engine: AsyncEngine, world: World, company: Company
) -> dict[str, str]:
    change = await make_change(engine, company, world.outsider, Role.EDITOR, Role.APPROVER)
    attachment = await make_attachment(
        engine, company, change, world.outsider, Role.EDITOR, Role.APPROVER
    )
    return {"change_id": str(change.id), "attachment_id": str(attachment.id)}


def _own_ci(world: World, company_id: UUID) -> UUID:
    """The CI of the TARGET company (A's CI for unknown companies: 404 comes first)."""
    return world.ci_b.id if company_id == world.b.id else world.ci_a.id


async def _foreign_ci(engine: AsyncEngine, world: World, company: Company) -> dict[str, str]:
    ci = await make_ci(engine, company, world.ci_type, name="Obcy obiekt")
    return {"ci_id": str(ci.id)}


MEMBER_CASES = tuple(c for c in CASES if c.access == "member")
ADMIN_CASES = tuple(c for c in CASES if c.access == "admin")
RESOURCE_CASES = tuple(c for c in CASES if c.foreign_resource is not None)


@dataclass(frozen=True)
class QueryIsolationCase:
    """A route with the query parameter ``company_id`` (the chosen company)."""

    method: str
    path: str  # the route path exactly as declared
    # Who succeeds for company A (sanity check that the 404 is about the company).
    allowed_personas: tuple[str, ...]
    # The admin path (app admin without membership) is accepted for any company.
    admin_path: bool = False

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"


QUERY_CASES: tuple[QueryIsolationCase, ...] = (
    QueryIsolationCase("POST", "/api/v1/audit/verify", ("auditor",), admin_path=True),
    # The admin reads any company chain (owner decision 2026-11-02, ADR 0015 §7).
    QueryIsolationCase("GET", "/api/v1/audit", ("auditor",), admin_path=True),
    # Stage 7: the report list of one company (ADR 0017); the admin reads any company on
    # the narrow read-only path.
    QueryIsolationCase("GET", "/api/v1/reports", ("approver", "auditor"), admin_path=True),
)


# Routes addressing a company-owned resource WITHOUT the company in the path or query
# (ADR 0017): the report id (``/reports/{report_id}``) and the company in the BODY
# (``POST /reports``). ``tests/test_isolation_api.py`` checks that a report of company B is
# answered exactly like a missing report for every member of A, and that ordering a report
# of B gives the same 404 as a non-existent company - with no side effect in B.
REPORT_RESOURCE_ROUTES: tuple[str, ...] = (
    "/api/v1/reports/{report_id}",
    "/api/v1/reports/{report_id}/download",
)
REPORT_BODY_ROUTES: tuple[str, ...] = ("/api/v1/reports",)
