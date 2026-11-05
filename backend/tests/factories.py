"""Test data built through the real services (audited as ``system``), connected as app_rw."""

from __future__ import annotations

import secrets
import string
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.auth.dev import issue_dev_token
from app.db import apply_company_scope
from app.domain.audit import Actor, VerifyResult
from app.domain.changes import ChangeAction
from app.models import (
    Attachment,
    Change,
    ChangeCategory,
    CiType,
    Company,
    ConfigurationItem,
    ReportExport,
    User,
)
from app.permissions import Role
from app.services import (
    attachments,
    audit,
    categories,
    changes,
    ci_types,
    companies,
    company_categories,
    configuration_items,
    memberships,
    users,
)
from tests.auth_helpers import DEV_SECRET

SYSTEM = Actor.system()


def random_prefix(length: int = 8) -> str:
    return "".join(secrets.choice(string.ascii_uppercase) for _ in range(length))


@asynccontextmanager
async def scoped(
    engine: AsyncEngine,
    company_ids: Sequence[UUID] = (),
    *,
    global_read: bool = False,
    admin_scope: bool = False,
) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
        await apply_company_scope(
            session, company_ids, global_audit_read=global_read, admin_scope=admin_scope
        )
        yield session


async def make_user(
    engine: AsyncEngine,
    *,
    admin: bool = False,
    active: bool = True,
    name: str | None = None,
) -> User:
    suffix = uuid4().hex[:10]
    async with scoped(engine) as session:
        return await users.create_user(
            session,
            actor=SYSTEM,
            external_id=f"test-{suffix}",
            email=f"user-{suffix}@example.com",
            display_name=name or f"Użytkownik {suffix}",
            is_app_admin=admin,
            is_active=active,
        )


async def make_company(engine: AsyncEngine, **kwargs: Any) -> Company:
    prefix = kwargs.pop("prefix", None) or random_prefix()
    async with scoped(engine, admin_scope=True) as session:
        return await companies.create_company(
            session,
            actor=SYSTEM,
            name=kwargs.pop("name", f"Spółka {prefix}"),
            prefix=prefix,
            **kwargs,
        )


async def grant(engine: AsyncEngine, company: Company, user: User, *roles: Role) -> None:
    async with scoped(engine, [company.id], admin_scope=True) as session:
        await memberships.set_member_roles(
            session, actor=SYSTEM, company_id=company.id, user_id=user.id, roles=set(roles)
        )


def random_category_code() -> str:
    """Never collides with the seed dictionary (CLAUDE.md §13 codes have no ``TST``)."""
    return "TST-" + uuid4().hex[:10].upper()


def random_ci_type_code() -> str:
    return "tst_" + uuid4().hex[:12]


async def make_category(
    engine: AsyncEngine, *, parent: ChangeCategory | None = None, **kwargs: Any
) -> ChangeCategory:
    async with scoped(engine, admin_scope=True) as session:
        return await categories.create_category(
            session,
            actor=SYSTEM,
            code=kwargs.pop("code", None) or random_category_code(),
            name=kwargs.pop("name", "Kategoria testowa"),
            parent_id=parent.id if parent is not None else None,
            **kwargs,
        )


async def make_ci_type(engine: AsyncEngine, **kwargs: Any) -> CiType:
    async with scoped(engine, admin_scope=True) as session:
        return await ci_types.create_ci_type(
            session,
            actor=SYSTEM,
            code=kwargs.pop("code", None) or random_ci_type_code(),
            name=kwargs.pop("name", "Typ testowy"),
        )


async def make_ci(
    engine: AsyncEngine, company: Company, ci_type: CiType, **kwargs: Any
) -> ConfigurationItem:
    async with scoped(engine, [company.id]) as session:
        row = await configuration_items.create_item(
            session,
            actor=SYSTEM,
            company=company,
            ci_type_id=ci_type.id,
            identifier=kwargs.pop("identifier", None) or f"CI-{uuid4().hex[:10].upper()}",
            name=kwargs.pop("name", "Obiekt testowy"),
            **kwargs,
        )
        return row.item


def token_for(user: User) -> str:
    return issue_dev_token(DEV_SECRET, user.external_id)[0]


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user)}"}


async def audit_entries(
    engine: AsyncEngine, entity_id: UUID, *, include_auth: bool = False
) -> list[Any]:
    """All audit entries about ``entity_id`` (any chain), oldest first.

    Authentication events (``entity_type = auth``: login, login_failed, access_denied —
    their ``entity_id`` is the user) are left out unless ``include_auth``: every first
    request with a new token logs the user in (ADR 0010).
    """
    async with AsyncSession(engine) as session, session.begin():
        # Listing all companies needs the admin path (RLS, ADR 0008); reading their audit
        # chains needs them in the company scope (admin_scope does not widen audit_log).
        await apply_company_scope(session, [], admin_scope=True)
        companies_ids = (await session.execute(text("SELECT id FROM companies"))).scalars().all()
        await apply_company_scope(session, list(companies_ids), global_audit_read=True)
        result = await session.execute(
            text(
                "SELECT * FROM audit_log WHERE entity_id = :id "
                "AND (CAST(:auth AS boolean) OR entity_type <> 'auth') "
                "ORDER BY occurred_at, company_id NULLS FIRST, seq"
            ),
            {"id": entity_id, "auth": include_auth},
        )
        return list(result.all())


async def verify(engine: AsyncEngine, company_id: UUID | None) -> VerifyResult:
    scope = [company_id] if company_id else []
    async with scoped(engine, scope, global_read=company_id is None) as session:
        return await audit.verify_chain(session, company_id)


@dataclass
class World:
    """Company A with one member per role, company B with an outsider, plus an admin."""

    a: Company
    b: Company
    admin: User
    approver: User
    editor: User
    auditor: User
    viewer: User
    outsider: User  # member of B only
    nobody: User  # no membership at all
    category: ChangeCategory  # an active top-level category (global dictionary)
    ci_type: CiType  # an active CI type (global dictionary)
    ci_a: ConfigurationItem  # a CI of company A
    ci_b: ConfigurationItem  # a CI of company B
    # Changes (only after ``add_changes``): a ready draft of A (author and assignee: the
    # editor, approver: the approver), a pending change of A, a draft of B, a file of A.
    draft_a: Change | None = None
    pending_a: Change | None = None
    draft_b: Change | None = None
    attachment_a: Attachment | None = None
    approved_a: Change | None = None  # approved by the approver, assignee: the editor
    implemented_a: Change | None = None  # implemented by the editor (assignee)
    # Reports (only after ``add_report``): a register report of A ordered by the auditor.
    report_a: ReportExport | None = None

    def persona(self, name: str) -> User:
        user: User = getattr(self, name)
        return user


PERSONAS = ("admin", "approver", "editor", "auditor", "viewer", "outsider", "nobody")


async def make_world(engine: AsyncEngine) -> World:
    a = await make_company(engine)
    b = await make_company(engine)
    ci_type = await make_ci_type(engine)
    world = World(
        a=a,
        b=b,
        admin=await make_user(engine, admin=True, name="Adam Administrator"),
        approver=await make_user(engine, name="Jan Zatwierdzający"),
        editor=await make_user(engine, name="Ewa Edytorska"),
        auditor=await make_user(engine, name="Alicja Audytorka"),
        viewer=await make_user(engine, name="Piotr Przeglądający"),
        outsider=await make_user(engine, name="Olga Obca"),
        nobody=await make_user(engine, name="Norbert Nikt"),
        category=await make_category(engine),
        ci_type=ci_type,
        ci_a=await make_ci(engine, a, ci_type, name="Zapora brzegowa A"),
        ci_b=await make_ci(engine, b, ci_type, name="Zapora brzegowa B"),
    )
    await grant(engine, a, world.approver, Role.APPROVER)
    await grant(engine, a, world.editor, Role.EDITOR)
    await grant(engine, a, world.auditor, Role.AUDITOR)
    await grant(engine, a, world.viewer, Role.VIEWER)
    await grant(engine, b, world.outsider, Role.EDITOR, Role.APPROVER)
    return world


def client_for(app: FastAPI) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    )


# --------------------------------------------------------------------------- changes


def change_actor(user: User, company: Company, *roles: Role) -> changes.ChangeActor:
    """The acting user as the API builds it (membership roles of the company)."""
    return changes.ChangeActor(
        audit=Actor(id=user.id, display=user.display_name, roles=tuple(r.value for r in roles)),
        user_id=user.id,
        roles=frozenset(roles),
    )


async def make_available(engine: AsyncEngine, company: Company, *cats: ChangeCategory) -> None:
    """Set the categories available in ``company`` (admin path, audited as system)."""
    async with scoped(engine, [company.id], admin_scope=True) as session:
        await company_categories.set_company_categories(
            session,
            actor=SYSTEM,
            company_id=company.id,
            assignments=[company_categories.Assignment(category_id=c.id) for c in cats],
        )


def ready_values(
    *,
    category: ChangeCategory,
    ci: Sequence[ConfigurationItem],
    assignee: User,
    approver: User | None,
    **overrides: Any,
) -> dict[str, Any]:
    """Fields of a normal, medium-risk change that passes readiness (window tomorrow)."""
    start = datetime.now(UTC) + timedelta(days=1)
    values: dict[str, Any] = {
        "title": "Nowa reguła na zaporze",
        "category_id": category.id,
        "change_type": "normal",
        "risk": "medium",
        "description": "Otwarcie portu 443 dla nowego serwera aplikacyjnego.",
        "implementation_plan": "1. Dodaj regułę. 2. Zapisz konfigurację. 3. Sprawdź ruch.",
        "rollback_plan": "Usuń regułę.",
        "assignee_id": assignee.id,
        "window_start": start,
        "window_end": start + timedelta(hours=2),
        "ci_ids": [c.id for c in ci],
    }
    if approver is not None:
        values["approver_id"] = approver.id
    values.update(overrides)
    return values


async def make_change(
    engine: AsyncEngine,
    company: Company,
    author: User,
    *roles: Role,
    values: dict[str, Any] | None = None,
) -> Change:
    async with scoped(engine, [company.id]) as session:
        return await changes.create_change(
            session,
            actor=change_actor(author, company, *roles),
            company=company,
            values=values or {"title": "Szkic"},
        )


async def act(
    engine: AsyncEngine,
    company: Company,
    change: Change,
    user: User,
    action: ChangeAction | str,
    *roles: Role,
    comment: str | None = None,
) -> Change:
    async with scoped(engine, [company.id]) as session:
        result = await changes.perform_action(
            session,
            actor=change_actor(user, company, *roles),
            company=company,
            change_id=change.id,
            action=ChangeAction(action),
            comment=comment,
        )
        return result.change


async def make_attachment(
    engine: AsyncEngine,
    company: Company,
    change: Change,
    user: User,
    *roles: Role,
    content: bytes = b"zawartosc",
    filename: str = "dowod.txt",
) -> Attachment:
    from tests.conftest import TEST_STORAGE

    remaining = [content]

    async def reader(_: int) -> bytes:
        return remaining.pop() if remaining else b""

    async with scoped(engine, [company.id]) as session:
        return await attachments.add_attachment(
            session,
            actor=change_actor(user, company, *roles),
            company=company,
            change_id=change.id,
            filename=filename,
            content_type="text/plain",
            reader=reader,
            storage_root=TEST_STORAGE,
            max_bytes=1024 * 1024,
        )


async def add_changes(engine: AsyncEngine, world: World) -> World:
    """Changes for the permission / isolation tests (``World.draft_a`` and the rest)."""
    await make_available(engine, world.a, world.category)
    await make_available(engine, world.b, world.category)
    ready = ready_values(
        category=world.category, ci=[world.ci_a], assignee=world.editor, approver=world.approver
    )
    world.draft_a = await make_change(engine, world.a, world.editor, Role.EDITOR, values=ready)
    pending = await make_change(engine, world.a, world.editor, Role.EDITOR, values=ready)
    world.pending_a = await act(engine, world.a, pending, world.editor, "submit", Role.EDITOR)
    world.draft_b = await make_change(
        engine,
        world.b,
        world.outsider,
        Role.EDITOR,
        Role.APPROVER,
        values={"title": "Szkic B", "ci_ids": [world.ci_b.id]},
    )
    world.attachment_a = await make_attachment(
        engine, world.a, world.draft_a, world.editor, Role.EDITOR
    )
    approved = await make_change(engine, world.a, world.editor, Role.EDITOR, values=ready)
    approved = await act(engine, world.a, approved, world.editor, "submit", Role.EDITOR)
    world.approved_a = await act(
        engine, world.a, approved, world.approver, "approve", Role.APPROVER
    )
    implemented = await make_change(engine, world.a, world.editor, Role.EDITOR, values=ready)
    for user, action, role in (
        (world.editor, "submit", Role.EDITOR),
        (world.approver, "approve", Role.APPROVER),
        (world.editor, "implement", Role.EDITOR),
    ):
        implemented = await act(engine, world.a, implemented, user, action, role)
    world.implemented_a = implemented
    return world


async def all_companies(api: AsyncClient, user: User) -> list[dict[str, Any]]:
    """Every page of ``GET /companies`` for ``user``: the session-wide test database holds
    hundreds of companies (one world per test), more than one page of 500."""
    items: list[dict[str, Any]] = []
    while True:
        response = await api.get(
            "/api/v1/companies", params={"limit": 500, "offset": len(items)}, headers=auth(user)
        )
        assert response.status_code == 200, response.text
        page = response.json()
        items.extend(page["items"])
        if not page["items"] or len(items) >= page["total"]:
            return items


# --------------------------------------------------------------------------- reports


def stub_pdf(html: str) -> bytes:
    """A stand-in renderer where WeasyPrint (Pango) is not installed - for permission and
    isolation tests only; PDF content tests are marked ``pdf`` and need the real one."""
    import hashlib

    return b"%PDF-1.7\n% stub " + hashlib.sha256(html.encode("utf-8")).hexdigest().encode()


class RecordingQueue:
    """``app.state.report_queue`` of the tests: records the jobs (run them explicitly)."""

    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    async def enqueue(self, job: dict[str, Any]) -> None:
        self.jobs.append(job)

    async def aclose(self) -> None:
        return None


def exporter_for(user: User, roles: dict[UUID, set[Role]] | None = None) -> Any:
    from app.services.reports import Exporter

    return Exporter(
        user_id=user.id,
        display_name=user.display_name,
        roles_by_company={c: frozenset(r.value for r in rs) for c, rs in (roles or {}).items()},
        is_app_admin=user.is_app_admin,
    )


WIDE_PERIOD = (datetime(2000, 1, 1, tzinfo=UTC), datetime(2100, 1, 1, tzinfo=UTC))


async def make_report(
    engine: AsyncEngine,
    companies: Sequence[Company],
    user: User,
    roles: dict[UUID, set[Role]],
    *,
    aggregate: bool = False,
    kind: str = "register",
    change: Change | None = None,
    include_audit_trail: bool = False,
    renderer: Any = stub_pdf,
    async_threshold: int = 200,
    queue: RecordingQueue | None = None,
) -> ReportExport:
    """A report generated through the service, as ``POST /reports`` does."""
    from app.db import set_current_user
    from app.domain.reports import ReportKind
    from app.services import reports
    from tests.conftest import TEST_STORAGE

    if kind == "register":
        filters = changes.ChangeFilters(period_from=WIDE_PERIOD[0], period_to=WIDE_PERIOD[1])
    else:
        filters = changes.ChangeFilters()
    async with scoped(engine, [c.id for c in companies]) as session:
        await set_current_user(session, user.id)
        return await reports.create_report(
            session,
            request=reports.ReportRequest(
                kind=ReportKind(kind),
                company=None if aggregate else companies[0],
                companies=list(companies),
                filters=filters,
                change_id=change.id if change else None,
                include_audit_trail=include_audit_trail,
            ),
            exporter=exporter_for(user, roles),
            options=reports.ReportOptions(
                storage_root=TEST_STORAGE, async_threshold=async_threshold, max_changes=5000
            ),
            renderer=renderer,
            enqueue=(queue or RecordingQueue()).enqueue,
        )


async def add_report(engine: AsyncEngine, world: World) -> World:
    """``World.report_a``: a register report of A generated for the auditor."""
    world.report_a = await make_report(
        engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}}
    )
    return world
