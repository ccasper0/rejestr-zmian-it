"""Sample changes for development (``python -m app.cli seed``, CLAUDE.md §11.7; ADR 0013 §9).

About 40 changes in ALFA, BETA and GAMMA in every status, including an emergency change
not approved within 24 h (a deviation), changes implemented without verification,
standard changes approved automatically by ``system``, rejected, rolled back and
cancelled changes, and comments.

Everything goes through the services and the state machine (no shortcut, no direct SQL):
each step is performed by the person the state machine requires (author / assignee:
``dev-editor``; designated approver and verifier: ``dev-approver``), so the audit chain
contains real transitions. The business clock of each step (``now`` of the services) is
SIMULATED in the past - the history spans the last weeks - while ``audit_log.occurred_at``
is, as always, the database clock at seeding time. Every audit entry written here carries
``context.source = "seed"`` and ``context.simulated_at`` so that sample history can never
be mistaken for real work.

Idempotent: changes are seeded only in a company that has none yet (a company with any
change belongs to its users). One transaction per company (only its chain).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import apply_company_scope
from app.domain.audit import Actor
from app.domain.changes import ChangeAction, ChangeType, Risk
from app.domain.companies import CompanyStatus
from app.errors import ProblemError
from app.models import Change, ChangeCategory, Company, ConfigurationItem, User
from app.services import changes, comments, companies, memberships, users

EDITOR = "dev-editor"
APPROVER = "dev-approver"

# Who performs a step (the state machine checks it anyway).
_ACTORS: dict[str, str] = {
    "submit": EDITOR,
    "implement": EDITOR,
    "rollback": EDITOR,
    "cancel": EDITOR,
    "approve": APPROVER,
    "reject": APPROVER,
    "return": APPROVER,
    "verify": APPROVER,
}


@dataclass(frozen=True, slots=True)
class Step:
    action: str  # a ChangeAction value or "comment"
    comment: str | None = None
    by: str | None = None  # default: _ACTORS
    late: bool = False  # after-the-fact approval of an emergency change after 24 h


@dataclass(frozen=True, slots=True)
class SeedChange:
    title: str
    category: str  # category code
    subcategory: str | None
    change_type: ChangeType
    risk: Risk
    ci: tuple[str, ...]
    days_ago: float
    steps: tuple[Step, ...] = ()
    ticket: str | None = None
    impact: str | None = None


def _s(*names: str) -> tuple[Step, ...]:
    return tuple(Step(n) for n in names)


N, S, E = ChangeType.NORMAL, ChangeType.STANDARD, ChangeType.EMERGENCY
LOW, MED, HIGH = Risk.LOW, Risk.MEDIUM, Risk.HIGH
FULL = _s("submit", "approve", "implement", "verify")
IMPLEMENTED = _s("submit", "approve", "implement")
APPROVED = _s("submit", "approve")
PENDING = _s("submit")
AUTO = _s("submit")  # standard: approved by system

SEED_CHANGES: dict[str, tuple[SeedChange, ...]] = {
    "ALFA": (
        SeedChange("Nowa reguła dostępu HTTPS do serwera ERP", "FW", "FW-RULES", N, MED,
                   ("FW-01", "VM-ERP-01"), 40, FULL, "SD-2101"),
        SeedChange("Aktualizacja firmware zapory brzegowej", "NET", "NET-FIRMWARE", N, HIGH,
                   ("FW-01",), 34, (*FULL[:3], Step("comment", "Wdrożono bez przerwy w usłudze."),
                                    FULL[3]), "SD-2107"),
        SeedChange("Krytyczna łatka kontrolera domeny", "PATCH", "PATCH-CRIT", E, HIGH,
                   ("SRV-DC-01",), 30, (Step("implement"), Step("approve"), Step("verify")),
                   "INC-3301"),
        SeedChange("Wyłączenie podatnego protokołu SMBv1", "SEC", None, E, HIGH,
                   ("SRV-FS-01",), 6, (Step("implement"),), "INC-3349",
                   impact="Starsze skanery sieciowe mogą utracić dostęp do udziałów."),
        SeedChange("Nadanie uprawnień do ERP dla działu zakupów", "ACC", "ACC-GRANT", S, LOW,
                   ("APP-ERP",), 25, (*AUTO, Step("implement"), Step("verify")), "SD-2140"),
        SeedChange("Dodanie użytkownika do grupy Księgowość", "ACC", "ACC-GROUP", S, LOW,
                   ("GRP-DOMAIN-ADMINS",), 3, AUTO, "SD-2188"),
        SeedChange("Zwiększenie zasobów maszyny ERP", "SRV", "SRV-RES", N, MED,
                   ("VM-ERP-01",), 20, IMPLEMENTED, "SD-2150"),
        SeedChange("Nowy VLAN dla drukarek", "NET", "NET-VLAN", N, MED,
                   ("SW-CORE-01", "SW-ACC-02"), 18, IMPLEMENTED, "SD-2155"),
        SeedChange("Zmiana harmonogramu kopii zapasowych ERP", "BKP", "BKP-SCHED", N, LOW,
                   ("VM-ERP-01",), 15,
                   (Step("submit"), Step("reject", "Harmonogram koliduje z zamknięciem miesiąca.")),
                   "SD-2160"),
        SeedChange("Aktualizacja kontrolera Wi-Fi", "NET", "NET-WIFI", N, HIGH,
                   ("WLC-01",), 14,
                   (*IMPLEMENTED,
                    Step("rollback", "Po aktualizacji punkty dostępowe traciły łączność.")),
                   "SD-2163"),
        SeedChange("Polityka haseł: 14 znaków", "GPO", "GPO-PWD", N, MED,
                   ("GRP-DOMAIN-ADMINS",), 4, APPROVED, "SD-2190"),
        SeedChange("Odnowienie certyfikatu portalu ERP", "SEC", "SEC-CERT", N, MED,
                   ("APP-ERP",), 2, PENDING, "SD-2194"),
        SeedChange("Reguła NAT dla nowego partnera EDI", "FW", "FW-NAT", N, MED,
                   ("FW-02",), 2,
                   (Step("submit"), Step("return", "Uzupełnij adresy IP partnera."),
                    Step("comment", "Czekam na adresy od partnera.", by=EDITOR)), "SD-2195"),
        SeedChange("Migracja serwera plików na nową macierz", "SRV", "SRV-MIGR", N, HIGH,
                   ("SRV-FS-01",), 1, (), "SD-2199"),
        SeedChange("Test odtworzenia kopii kontrolera domeny", "BKP", "BKP-TEST", N, LOW,
                   ("SRV-DC-01",), 9, (Step("cancel"),), None),
        SeedChange("Wymiana przełącznika dostępowego", "NET", None, N, MED,
                   ("SW-ACC-02",), 1, PENDING, "SD-2201"),
    ),
    "BETA": (
        SeedChange("Reguła VPN dla pracy zdalnej", "FW", "FW-VPN", N, MED,
                   ("FW-01",), 38, FULL, "B-501"),
        SeedChange("Aktualizacja systemu CRM do wersji 8.2", "APP", "APP-VER", N, HIGH,
                   ("APP-CRM", "SRV-01"), 31, FULL, "B-505"),
        SeedChange("Poprawka bezpieczeństwa serwera WWW", "PATCH", "PATCH-CRIT", E, HIGH,
                   ("VM-WEB-01",), 22,
                   (Step("implement"), Step("approve", late=True), Step("verify")), "B-INC-77"),
        SeedChange("Konto serwisowe dla nowej kopii zapasowej", "ACC", "ACC-SVC", S, LOW,
                   ("SVC-BACKUP",), 19, (*AUTO, Step("implement"), Step("verify")), "B-512"),
        SeedChange("Nowy punkt dostępowy w sali konferencyjnej", "NET", "NET-WIFI", N, LOW,
                   ("AP-01", "SW-01"), 16, IMPLEMENTED, "B-515"),
        SeedChange("Retencja kopii NAS: 90 dni", "BKP", "BKP-RET", N, MED,
                   ("NAS-01",), 12, FULL, "B-519"),
        SeedChange("Integracja CRM z systemem fakturowym", "APP", "APP-INT", N, MED,
                   ("APP-CRM",), 10,
                   (Step("submit"), Step("reject", "Brak zgody właściciela procesu finansów.")),
                   "B-522"),
        SeedChange("Zmiana grupy Finanse - nowa pracownica", "ACC", "ACC-GROUP", S, LOW,
                   ("GRP-FINANSE",), 8, AUTO, "B-524"),
        SeedChange("Aktualizacja systemu operacyjnego serwera aplikacyjnego", "PATCH",
                   "PATCH-OS", N, MED, ("SRV-01",), 7,
                   (*IMPLEMENTED, Step("rollback", "Aplikacja nie uruchomiła się po restarcie.")),
                   "B-527"),
        SeedChange("Wdrożenie agenta EDR na serwerach", "SEC", "SEC-EDR", N, MED,
                   ("SRV-01", "VM-WEB-01"), 3, APPROVED, "B-530"),
        SeedChange("Nowa maszyna dla środowiska testowego CRM", "SRV", "SRV-NEW", N, LOW,
                   ("SRV-01",), 2, PENDING, "B-532"),
        SeedChange("Zmiana routingu do oddziału", "NET", "NET-VLAN", N, MED,
                   ("SW-01",), 1, (), "B-534"),
        SeedChange("Wyłączenie starego serwera WWW", "SRV", "SRV-DECOM", N, LOW,
                   ("VM-WEB-01",), 5, (Step("cancel"),), None),
    ),
    "GAMMA": (
        SeedChange("Reguła zapory dla skanerów magazynowych", "FW", "FW-RULES", N, MED,
                   ("FW-01",), 35, FULL, "G-101"),
        SeedChange("Aktualizacja WMS do wersji 5", "APP", "APP-VER", N, HIGH,
                   ("APP-WMS", "VM-01"), 28, FULL, "G-104"),
        SeedChange("Nadanie dostępu do WMS dla brygadzisty", "ACC", "ACC-GRANT", S, LOW,
                   ("GRP-IT",), 21, (*AUTO, Step("implement"), Step("verify")), "G-108"),
        SeedChange("Zwiększenie dysku maszyny WMS", "SRV", "SRV-RES", N, LOW,
                   ("VM-01",), 13, IMPLEMENTED, "G-112"),
        SeedChange("Polityka blokady ekranu na terminalach", "GPO", "GPO-GPO", N, LOW,
                   ("GRP-IT",), 11, FULL, "G-115"),
        SeedChange("Firmware przełącznika magazynowego", "NET", "NET-FIRMWARE", N, MED,
                   ("SW-01",), 6, APPROVED, "G-118"),
        SeedChange("Certyfikat dla portalu dostawców", "SEC", "SEC-CERT", N, MED,
                   ("APP-WMS",), 2, PENDING, "G-120"),
        SeedChange("Kopie zapasowe serwera plików co 4 h", "BKP", "BKP-SCHED", N, LOW,
                   ("SRV-01",), 1, (), "G-121"),
        SeedChange("Integracja WMS z systemem kurierskim", "APP", "APP-INT", N, MED,
                   ("APP-WMS",), 9,
                   (Step("submit"), Step("approve"),
                    Step("comment", "Wdrożenie po inwentaryzacji.", by=APPROVER)), "G-117"),
        SeedChange("Odebranie uprawnień byłemu pracownikowi", "ACC", "ACC-REVOKE", S, LOW,
                   ("GRP-IT",), 4, (*AUTO, Step("implement")), "G-119"),
        SeedChange("Przeniesienie serwera plików do szafy B", "SRV", "SRV-MIGR", N, HIGH,
                   ("SRV-01",), 3,
                   (Step("submit"), Step("return", "Dodaj plan wycofania na wypadek awarii.")),
                   "G-122"),
    ),
}  # fmt: skip

KSC_REQUIREMENT = "ISO/IEC 27001:2022 A.8.32; uoKSC"


@dataclass
class SeedChangesReport:
    created: int = 0
    lines: list[str] = field(default_factory=list)


def _window(spec: SeedChange, created: datetime) -> tuple[datetime, datetime]:
    if spec.change_type is ChangeType.EMERGENCY:
        return created - timedelta(minutes=30), created + timedelta(hours=2)
    start = created + timedelta(days=1)
    return start, start + timedelta(hours=2)


def _step_time(
    step: Step, previous: datetime, window_start: datetime, spec: SeedChange
) -> datetime:
    if step.action == "implement" and spec.change_type is not ChangeType.EMERGENCY:
        return max(previous, window_start) + timedelta(minutes=30)
    if step.action == "verify":
        return previous + timedelta(days=1)
    if step.action == "approve" and spec.change_type is ChangeType.EMERGENCY:
        return previous + timedelta(hours=30 if step.late else 6)
    return previous + timedelta(hours=1)


async def _has_changes(session: AsyncSession, company_id: UUID) -> bool:
    count = (
        await session.execute(select(func.count()).where(Change.company_id == company_id))
    ).scalar_one()
    return bool(count)


async def _actor(session: AsyncSession, company: Company, user: User) -> changes.ChangeActor:
    roles = await memberships.user_roles_in(session, company.id, user.id)
    return changes.ChangeActor(
        audit=Actor(id=user.id, display=user.display_name, roles=tuple(r.value for r in roles)),
        user_id=user.id,
        roles=roles,
    )


def _marker(at: datetime) -> dict[str, object]:
    return {"source": "seed", "simulated_at": at}


async def _play(
    session: AsyncSession,
    *,
    company: Company,
    spec: SeedChange,
    values: dict[str, object],
    actors: dict[str, changes.ChangeActor],
    created_at: datetime,
    window_start: datetime,
    now: datetime,
) -> str:
    """Create the change and perform its steps at their simulated times."""
    change = await changes.create_change(
        session,
        actor=actors[EDITOR],
        company=company,
        values=values,
        now=created_at,
        audit_context=_marker(created_at),
    )
    clock = created_at
    for step in spec.steps:
        clock = _step_time(step, clock, window_start, spec)
        if clock > now:
            raise ValueError(f"seed step {step.action} of {spec.title!r} is in the future")
        who = actors[step.by or _ACTORS.get(step.action, EDITOR)]
        if step.action == "comment":
            await comments.add_comment(
                session,
                actor=who,
                company=company,
                change_id=change.id,
                body=step.comment or "",
                now=clock,
                audit_context=_marker(clock),
            )
            continue
        await changes.perform_action(
            session,
            actor=who,
            company=company,
            change_id=change.id,
            action=ChangeAction(step.action),
            comment=step.comment,
            now=clock,
            audit_context=_marker(clock),
        )
    return change.number


async def _seed_company(
    session: AsyncSession,
    *,
    company: Company,
    specs: tuple[SeedChange, ...],
    people: dict[str, User],
    category_ids: dict[str, UUID],
    now: datetime,
    report: SeedChangesReport,
) -> None:
    ci_by_identifier = {
        ci.identifier: ci
        for ci in (
            await session.execute(
                select(ConfigurationItem).where(ConfigurationItem.company_id == company.id)
            )
        ).scalars()
    }
    actors = {key: await _actor(session, company, user) for key, user in people.items()}
    editor, approver = people[EDITOR], people[APPROVER]
    for spec in specs:
        label = f"zmiana {company.prefix}: {spec.title}"
        cis = [ci_by_identifier.get(i) for i in spec.ci]
        missing = [i for i, ci in zip(spec.ci, cis, strict=True) if ci is None or not ci.is_active]
        codes = [c for c in (spec.category, spec.subcategory) if c is not None]
        if missing or any(c not in category_ids for c in codes):
            report.lines.append(f"{label}: pominięto (brak CI lub kategorii)")
            continue
        created_at = now - timedelta(days=spec.days_ago)
        start, end = _window(spec, created_at)
        values: dict[str, object] = {
            "title": spec.title,
            "category_id": category_ids[spec.category],
            "subcategory_id": category_ids[spec.subcategory] if spec.subcategory else None,
            "change_type": spec.change_type.value,
            "risk": spec.risk.value,
            "description": f"{spec.title}. Zmiana zgłoszona w ramach bieżącego utrzymania.",
            "implementation_plan": "1. Przygotowanie i kopia konfiguracji.\n2. Wdrożenie.\n"
            "3. Testy po wdrożeniu.",
            "rollback_plan": "Przywrócenie konfiguracji z kopii wykonanej przed wdrożeniem.",
            "impact": spec.impact or "Brak przerwy w działaniu usług.",
            "ticket_ref": spec.ticket,
            "assignee_id": editor.id,
            "approver_id": approver.id,
            "verifier_id": approver.id,
            "window_start": start,
            "window_end": end,
            "ci_ids": [ci.id for ci in cis if ci is not None],
        }
        if company.is_ksc_entity:
            values["requirement_ref"] = KSC_REQUIREMENT

        try:
            async with session.begin_nested():
                number = await _play(
                    session,
                    company=company,
                    spec=spec,
                    values=values,
                    actors=actors,
                    created_at=created_at,
                    window_start=start,
                    now=now,
                )
        except ProblemError as exc:
            # Data the seed cannot reconcile (e.g. roles edited by an admin): this change
            # is rolled back entirely (savepoint), the others are seeded.
            report.lines.append(f"{label}: pominięto ({exc.code}: {exc.detail})")
            continue
        report.created += 1
        report.lines.append(f"{label}: utworzona ({number})")


async def seed_changes(
    sessionmaker: async_sessionmaker[AsyncSession], *, now: datetime | None = None
) -> SeedChangesReport:
    """Requires ``seed_identity``, ``seed_dictionaries`` and ``seed_inventory``."""
    report = SeedChangesReport()
    people: dict[str, User] = {}
    category_ids: dict[str, UUID] = {}
    async with sessionmaker() as session, session.begin():
        for external_id in (EDITOR, APPROVER):
            user = await users.get_user_by_external_id(session, external_id)
            if user is None or not user.is_active:
                report.lines.append(f"zmiany: pominięto (brak aktywnego użytkownika {external_id})")
                return report
            people[external_id] = user
        rows = (await session.execute(select(ChangeCategory))).scalars().all()
        category_ids = {c.code: c.id for c in rows if c.is_active}
        clock = now or await changes.db_now(session)

    for prefix, specs in SEED_CHANGES.items():
        async with sessionmaker() as session, session.begin():
            await apply_company_scope(session, [], admin_scope=True)
            company = await companies.get_company_by_prefix(session, prefix)
            if company is None or company.status == CompanyStatus.ARCHIVED:
                report.lines.append(f"zmiany w {prefix}: pominięto (brak lub zarchiwizowana)")
                continue
            await apply_company_scope(session, [company.id])
            if await _has_changes(session, company.id):
                report.lines.append(f"zmiany w {prefix}: istnieją, seed ich nie zmienia")
                continue
            await _seed_company(
                session,
                company=company,
                specs=specs,
                people=people,
                category_ids=category_ids,
                now=clock,
                report=report,
            )
    return report
