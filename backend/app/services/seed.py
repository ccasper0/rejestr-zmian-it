"""Sample identities for development (``python -m app.cli seed``, CLAUDE.md §11.7).

Idempotent and created ONLY through the services, so every row is audited with the
``system`` actor. Existing rows are never changed or removed: missing users, companies
and roles are added, roles granted by hand are kept.

Transactions follow the lock order of the audit chains (company chains before the global
one, ADR 0006 §7) by never mixing them: (1) users + companies -> global chain,
(2) memberships -> company chains, (3) default approvers -> global chain,
(4) dictionaries (CI types, change categories of CLAUDE.md §13) -> global chain,
(5) per company: available categories and sample CI -> that company's chain only.

The dictionaries (4) are reference data, not sample data: ``seed_dictionaries`` is also
run alone by ``python -m app.cli seed-dictionaries``, allowed in production (ADR 0011).
(6) per company: sample changes (``app.services.seed_changes``) -> that company's chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import apply_company_scope
from app.domain.audit import Actor
from app.domain.companies import CompanyStatus
from app.domain.dictionaries import Risk
from app.models import ChangeCategory, CiType, Company, ConfigurationItem, User
from app.permissions import Role
from app.services import (
    categories,
    ci_types,
    companies,
    company_categories,
    configuration_items,
    memberships,
    users,
)
from app.services.seed_changes import seed_changes


@dataclass(frozen=True, slots=True)
class SeedUser:
    external_id: str
    display_name: str
    email: str
    is_app_admin: bool = False
    roles: dict[str, frozenset[Role]] = field(default_factory=dict)  # prefix -> roles


@dataclass(frozen=True, slots=True)
class SeedCompany:
    prefix: str
    name: str
    is_ksc_entity: bool = False
    default_approver: str | None = None  # external_id


SEED_COMPANIES: tuple[SeedCompany, ...] = (
    SeedCompany("ALFA", "Alfa S.A.", is_ksc_entity=True, default_approver="dev-approver"),
    SeedCompany("BETA", "Beta sp. z o.o.", default_approver="dev-approver"),
    SeedCompany("GAMMA", "Gamma sp. z o.o.", default_approver="dev-approver"),
)

SEED_USERS: tuple[SeedUser, ...] = (
    # App admin: deliberately WITHOUT company roles (segregation of duties, §5).
    SeedUser("dev-admin", "Adam Administrator", "admin@example.com", is_app_admin=True),
    SeedUser(
        "dev-editor",
        "Ewa Edytorska",
        "editor@example.com",
        roles={c.prefix: frozenset({Role.EDITOR}) for c in SEED_COMPANIES},
    ),
    SeedUser(
        "dev-approver",
        "Jan Zatwierdzający",
        "approver@example.com",
        # Approver in every company: the sample changes of stage 4 need one (four eyes).
        roles={c.prefix: frozenset({Role.APPROVER}) for c in SEED_COMPANIES},
    ),
    SeedUser(
        "dev-auditor",
        "Alicja Audytorka",
        "auditor@example.com",
        roles={c.prefix: frozenset({Role.AUDITOR}) for c in SEED_COMPANIES},
    ),
    SeedUser(
        "dev-viewer",
        "Piotr Przeglądający",
        "viewer@example.com",
        roles={"GAMMA": frozenset({Role.VIEWER})},
    ),
)


@dataclass
class SeedReport:
    created: int = 0
    lines: list[str] = field(default_factory=list)

    def add(self, line: str, *, created: bool) -> None:
        self.lines.append(line)
        if created:
            self.created += 1


async def seed_identity(sessionmaker: async_sessionmaker[AsyncSession]) -> SeedReport:
    actor = Actor.system()
    report = SeedReport()
    user_ids: dict[str, UUID] = {}
    company_ids: dict[str, UUID] = {}

    # (1) Users and companies — global audit chain.
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, [], admin_scope=True)
        for spec in SEED_USERS:
            user = await users.get_user_by_external_id(session, spec.external_id)
            created = user is None
            if user is None:
                user = await users.create_user(
                    session,
                    actor=actor,
                    external_id=spec.external_id,
                    email=spec.email,
                    display_name=spec.display_name,
                    is_app_admin=spec.is_app_admin,
                    context={"source": "seed"},
                )
            user_ids[spec.external_id] = user.id
            report.add(
                f"użytkownik {spec.external_id}: {'utworzony' if created else 'istnieje'}",
                created=created,
            )
        for company_spec in SEED_COMPANIES:
            company = await companies.get_company_by_prefix(session, company_spec.prefix)
            created = company is None
            if company is None:
                company = await companies.create_company(
                    session,
                    actor=actor,
                    name=company_spec.name,
                    prefix=company_spec.prefix,
                    is_ksc_entity=company_spec.is_ksc_entity,
                )
            company_ids[company_spec.prefix] = company.id
            report.add(
                f"spółka {company_spec.prefix}: {'utworzona' if created else 'istnieje'}",
                created=created,
            )

    # (2) Roles — audit chains of the companies (only missing roles are added).
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, list(company_ids.values()), admin_scope=True)
        for spec in SEED_USERS:
            for prefix, wanted in spec.roles.items():
                company_id, user_id = company_ids[prefix], user_ids[spec.external_id]
                current = await memberships.user_roles_in(session, company_id, user_id)
                missing = wanted - current
                if missing:
                    await memberships.set_member_roles(
                        session,
                        actor=actor,
                        company_id=company_id,
                        user_id=user_id,
                        roles=current | wanted,
                    )
                roles = ", ".join(sorted(r.value for r in wanted))
                report.add(
                    f"role {spec.external_id} w {prefix} ({roles}): "
                    f"{'nadane' if missing else 'istnieją'}",
                    created=bool(missing),
                )

    # (3) Default approvers — global chain; set only when empty. The companies must be in
    # the scope: RLS allows UPDATE of a company only on the admin path AND within the
    # transaction scope (ADR 0008).
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, list(company_ids.values()), admin_scope=True)
        for company_spec in SEED_COMPANIES:
            if company_spec.default_approver is None:
                continue
            company = await companies.get_company(session, company_ids[company_spec.prefix])
            if company is None or company.default_approver_id is not None:
                continue
            await companies.update_company(
                session,
                actor=actor,
                company_id=company.id,
                changes={"default_approver_id": user_ids[company_spec.default_approver]},
            )
            report.add(
                f"spółka {company_spec.prefix}: domyślny zatwierdzający "
                f"{company_spec.default_approver}",
                created=True,
            )
    return report


# --------------------------------------------------------------------------- dictionaries


@dataclass(frozen=True, slots=True)
class SeedCategory:
    code: str
    name: str
    requires_approval: bool
    default_risk: Risk
    # (code suffix, name, requires_approval, default_risk) - None = as the category
    subcategories: tuple[tuple[str, str, bool | None, Risk | None], ...] = ()
    requires_ci_owner_consent: bool = False


def _subs(*items: tuple[str, str]) -> tuple[tuple[str, str, bool | None, Risk | None], ...]:
    return tuple((suffix, name, None, None) for suffix, name in items)


# CLAUDE.md §13. ACC is a standard category (no approval) EXCEPT privileged accounts:
# modelled as the subcategory ACC-PRIV requiring approval - a subcategory can only tighten
# its category (ADR 0011 §3). OT additionally needs the CI owner's consent (stage 4).
SEED_CATEGORIES: tuple[SeedCategory, ...] = (
    SeedCategory(
        "ACC",
        "Konta i uprawnienia",
        False,
        Risk.LOW,
        (
            *_subs(
                ("GRANT", "Nadanie uprawnień"),
                ("REVOKE", "Odebranie uprawnień"),
                ("GROUP", "Zmiana grupy"),
                ("SVC", "Konto serwisowe"),
            ),
            ("PRIV", "Konto uprzywilejowane", True, Risk.HIGH),
        ),
    ),
    SeedCategory(
        "NET",
        "Sieć",
        True,
        Risk.MEDIUM,
        _subs(("VLAN", "VLAN / routing"), ("FIRMWARE", "Firmware urządzeń"), ("WIFI", "Wi-Fi")),
    ),
    SeedCategory(
        "FW",
        "Firewall / sieć",
        True,
        Risk.MEDIUM,
        _subs(("RULES", "Reguły dostępu"), ("NAT", "NAT"), ("VPN", "VPN")),
    ),
    SeedCategory(
        "SRV",
        "Serwery / wirtualizacja",
        True,
        Risk.MEDIUM,
        _subs(
            ("NEW", "Nowy serwer / VM"),
            ("RES", "Zasoby"),
            ("MIGR", "Migracja"),
            ("DECOM", "Wyłączenie"),
        ),
    ),
    SeedCategory(
        "PATCH",
        "Aktualizacje i łatki",
        True,
        Risk.MEDIUM,
        (
            *_subs(("OS", "System operacyjny"), ("APP", "Aplikacje")),
            ("CRIT", "Krytyczne", None, Risk.HIGH),
        ),
    ),
    SeedCategory(
        "BKP",
        "Kopie zapasowe",
        True,
        Risk.LOW,
        _subs(("SCHED", "Harmonogram"), ("RET", "Retencja"), ("TEST", "Odtworzenie testowe")),
    ),
    SeedCategory(
        "GPO",
        "Polityki domenowe",
        True,
        Risk.MEDIUM,
        _subs(("GPO", "GPO"), ("PWD", "Polityki haseł"), ("MDM", "MDM")),
    ),
    SeedCategory(
        "APP",
        "Aplikacje biznesowe",
        True,
        Risk.MEDIUM,
        _subs(("CONF", "Konfiguracja"), ("VER", "Wersja"), ("INT", "Integracje")),
    ),
    SeedCategory(
        "SEC",
        "Bezpieczeństwo",
        True,
        Risk.MEDIUM,
        _subs(("EDR", "EDR / AV"), ("SIEM", "SIEM"), ("CERT", "Certyfikaty")),
    ),
    SeedCategory(
        "OT",
        "Systemy OT / przemysłowe",
        True,
        Risk.HIGH,
        _subs(("CONF", "Konfiguracja"), ("UPD", "Aktualizacja")),
        requires_ci_owner_consent=True,  # + the CI owner's consent (§13, ADR 0012 §5)
    ),
)

SEED_CATEGORY_CODES: tuple[str, ...] = tuple(
    code
    for c in SEED_CATEGORIES
    for code in (c.code, *(f"{c.code}-{sub[0]}" for sub in c.subcategories))
)

# CLAUDE.md §4.1 with Polish display names.
SEED_CI_TYPES: tuple[tuple[str, str], ...] = (
    ("server", "Serwer"),
    ("vm", "Maszyna wirtualna"),
    ("network_device", "Urządzenie sieciowe"),
    ("firewall", "Zapora sieciowa (firewall)"),
    ("account", "Konto"),
    ("group", "Grupa"),
    ("application", "Aplikacja"),
    ("ot_system", "System OT / przemysłowy"),
    ("other", "Inny"),
)
SEED_CI_TYPE_CODES: tuple[str, ...] = tuple(code for code, _ in SEED_CI_TYPES)


def _status(created: bool, *, feminine: bool = False) -> str:
    if created:
        return "utworzona" if feminine else "utworzony"
    return "istnieje"


async def seed_dictionaries(
    sessionmaker: async_sessionmaker[AsyncSession], *, context: dict[str, object] | None = None
) -> SeedReport:
    """CI types and change categories (global chain, one transaction). Only missing codes
    are added; existing entries (possibly edited by an admin) are never changed.

    ``context`` (e.g. the CLI operator: source, command, os_user, host) is added to the
    ``context`` of every audit entry written - the command may run in production."""
    actor = Actor.system()
    report = SeedReport()
    async with sessionmaker() as session, session.begin():
        # Dictionaries are written only on the explicit admin path (RLS, migration 0006).
        await apply_company_scope(session, [], admin_scope=True)
        for code, name in SEED_CI_TYPES:
            created = await ci_types.get_ci_type_by_code(session, code) is None
            if created:
                await ci_types.create_ci_type(
                    session, actor=actor, code=code, name=name, context=context
                )
            report.add(f"typ obiektu {code}: {_status(created)}", created=created)
        for spec in SEED_CATEGORIES:
            root = await categories.get_category_by_code(session, spec.code)
            created = root is None
            if root is None:
                root = await categories.create_category(
                    session,
                    actor=actor,
                    code=spec.code,
                    name=spec.name,
                    requires_approval=spec.requires_approval,
                    default_risk=spec.default_risk,
                    requires_ci_owner_consent=spec.requires_ci_owner_consent,
                    context=context,
                )
            report.add(f"kategoria {spec.code}: {_status(created, feminine=True)}", created=created)
            for suffix, name, requires_approval, risk in spec.subcategories:
                code = f"{spec.code}-{suffix}"
                created = await categories.get_category_by_code(session, code) is None
                if created:
                    await categories.create_category(
                        session,
                        actor=actor,
                        code=code,
                        name=name,
                        parent_id=root.id,
                        requires_approval=requires_approval,
                        default_risk=risk,
                        context=context,
                    )
                report.add(
                    f"podkategoria {code}: {_status(created, feminine=True)}", created=created
                )
    return report


# --------------------------------------------------------------------------- company inventory


@dataclass(frozen=True, slots=True)
class SeedCi:
    identifier: str
    ci_type: str
    name: str
    owner: str | None = None  # external_id of a member of the company
    active: bool = True
    description: str | None = None


ALL_ROOTS: tuple[str, ...] = tuple(c.code for c in SEED_CATEGORIES)

# prefix -> available categories (code -> approver override external_id or None)
SEED_COMPANY_CATEGORIES: dict[str, dict[str, str | None]] = {
    "ALFA": {**dict.fromkeys(ALL_ROOTS), "FW": "dev-approver"},
    "BETA": dict.fromkeys(c for c in ALL_ROOTS if c != "OT"),
    "GAMMA": dict.fromkeys(c for c in ALL_ROOTS if c != "OT"),
}

SEED_CI: dict[str, tuple[SeedCi, ...]] = {
    "ALFA": (
        SeedCi("FW-01", "firewall", "Zapora brzegowa (klaster HA)", owner="dev-approver"),
        SeedCi("FW-02", "firewall", "Zapora strefy DMZ", owner="dev-approver"),
        SeedCi("SW-CORE-01", "network_device", "Przełącznik rdzeniowy"),
        SeedCi("SW-ACC-02", "network_device", "Przełącznik dostępowy - piętro 2"),
        SeedCi("WLC-01", "network_device", "Kontroler sieci Wi-Fi"),
        SeedCi("SRV-DC-01", "server", "Kontroler domeny", owner="dev-editor"),
        SeedCi("SRV-FS-01", "server", "Serwer plików"),
        SeedCi("VM-ERP-01", "vm", "ERP - serwer aplikacyjny", owner="dev-editor"),
        SeedCi("APP-ERP", "application", "System ERP", owner="dev-editor"),
        SeedCi("ADM-JKOWALSKI", "account", "Konto administracyjne adm.jkowalski"),
        SeedCi("GRP-DOMAIN-ADMINS", "group", "Grupa Domain Admins"),
        SeedCi(
            "OT-SCADA-01",
            "ot_system",
            "SCADA - linia produkcyjna 1",
            description="Sieć przemysłowa; okna serwisowe uzgadniane z utrzymaniem ruchu.",
        ),
        SeedCi("SRV-MAIL-OLD", "server", "Wycofany serwer pocztowy", active=False),
    ),
    "BETA": (
        SeedCi("FW-01", "firewall", "Zapora główna", owner="dev-editor"),
        SeedCi("SW-01", "network_device", "Przełącznik biurowy"),
        SeedCi("AP-01", "network_device", "Punkt dostępowy - biuro"),
        SeedCi("SRV-01", "server", "Serwer aplikacyjny"),
        SeedCi("VM-WEB-01", "vm", "Serwer WWW"),
        SeedCi("VM-WEB-OLD", "vm", "Stary serwer WWW", active=False),
        SeedCi("APP-CRM", "application", "System CRM"),
        SeedCi("SVC-BACKUP", "account", "Konto serwisowe kopii zapasowych"),
        SeedCi("GRP-FINANSE", "group", "Finanse - użytkownicy"),
        SeedCi("NAS-01", "other", "Macierz NAS kopii zapasowych"),
    ),
    "GAMMA": (
        SeedCi("FW-01", "firewall", "Zapora główna"),
        SeedCi("SW-01", "network_device", "Przełącznik magazynowy"),
        SeedCi("SRV-01", "server", "Serwer plików i druku", owner="dev-viewer"),
        SeedCi("VM-01", "vm", "Maszyna wirtualna WMS"),
        SeedCi("APP-WMS", "application", "WMS - system magazynowy", owner="dev-viewer"),
        SeedCi("LOCAL-ADMIN", "account", "Lokalne konto administratora", active=False),
        SeedCi("GRP-IT", "group", "Dział IT"),
        SeedCi("PRN-01", "other", "Drukarka etykiet", active=False),
    ),
}


async def _eligible(
    session: AsyncSession, company_id: UUID, user: User | None, role: Role | None
) -> bool:
    """Active user with ``role`` (``None``: any role) in the company."""
    if user is None or not user.is_active:
        return False
    roles = await memberships.user_roles_in(session, company_id, user.id)
    return bool(roles) if role is None else role in roles


async def _seed_company_categories(
    session: AsyncSession,
    *,
    actor: Actor,
    company_id: UUID,
    planned: dict[str, str | None],
    categories_by_code: dict[str, ChangeCategory],
    users_by_external_id: dict[str, User],
) -> tuple[list[str], list[str]]:
    """Set the planned categories ONLY in a company without any categories yet.

    Once a company has categories they belong to the admin: a category withdrawn on
    purpose is never restored by a later seed. Categories missing or inactive in the
    dictionary and overrides that are not active approvers of the company are skipped with
    a note (never an error). Returns (added codes, notes).
    """
    if await company_categories.list_company_categories(session, company_id):
        return [], ["już ustawione, seed ich nie zmienia"]
    notes: list[str] = []
    added: list[str] = []
    wanted: list[company_categories.Assignment] = []
    for code, override in planned.items():
        category = categories_by_code.get(code)
        if category is None or not category.is_active or category.parent_id is not None:
            notes.append(f"pominięto {code} (brak w słowniku lub nieaktywna)")
            continue
        approver_id = None
        if override is not None:
            user = users_by_external_id.get(override)
            if await _eligible(session, company_id, user, Role.APPROVER):
                approver_id = user.id if user is not None else None
            else:
                notes.append(f"{code}: pominięto zatwierdzającego {override} (brak roli approver)")
        wanted.append(
            company_categories.Assignment(category_id=category.id, approver_override_id=approver_id)
        )
        added.append(code)
    if wanted:
        await company_categories.set_company_categories(
            session, actor=actor, company_id=company_id, assignments=wanted
        )
    return sorted(added), notes


async def _ci_exists(session: AsyncSession, company_id: UUID, identifier: str) -> bool:
    found = await session.execute(
        select(ConfigurationItem.id).where(
            ConfigurationItem.company_id == company_id,
            func.lower(ConfigurationItem.identifier) == identifier.lower(),
        )
    )
    return found.first() is not None


async def _seed_company_ci(
    session: AsyncSession,
    *,
    actor: Actor,
    company: Company,
    specs: tuple[SeedCi, ...],
    types_by_code: dict[str, CiType],
    users_by_external_id: dict[str, User],
    report: SeedReport,
) -> None:
    for spec in specs:
        label = f"obiekt {company.prefix}/{spec.identifier}"
        if await _ci_exists(session, company.id, spec.identifier):
            report.add(f"{label}: istnieje", created=False)
            continue
        ci_type = types_by_code.get(spec.ci_type)
        if ci_type is None or not ci_type.is_active:
            report.add(
                f"{label}: pominięto (typ {spec.ci_type} brak lub nieaktywny)", created=False
            )
            continue
        owner = users_by_external_id.get(spec.owner) if spec.owner else None
        if owner is not None and not await _eligible(session, company.id, owner, None):
            report.add(f"{label}: bez właściciela {spec.owner} (nie jest członkiem)", created=False)
            owner = None
        row = await configuration_items.create_item(
            session,
            actor=actor,
            company=company,
            ci_type_id=ci_type.id,
            identifier=spec.identifier,
            name=spec.name,
            description=spec.description,
            owner_user_id=owner.id if owner is not None else None,
        )
        if not spec.active:
            await configuration_items.update_item(
                session,
                actor=actor,
                company=company,
                ci_id=row.item.id,
                changes={"is_active": False},
            )
        report.add(f"{label}: utworzony", created=True)


async def seed_inventory(sessionmaker: async_sessionmaker[AsyncSession]) -> SeedReport:
    """Available categories and sample CI, one transaction per company (its chain only).

    Requires ``seed_identity`` and ``seed_dictionaries``. Categories are set only in a
    company that has none yet (``_seed_company_categories``); CI are created only when
    their identifier is free, planned inactive CI are deactivated right after creation
    (``create`` + ``deactivate`` in the audit log). Inactive dictionary entries and
    ineligible people are skipped with a note. Archived companies are skipped.
    """
    actor = Actor.system()
    report = SeedReport()
    users_by_external_id: dict[str, User] = {}
    categories_by_code: dict[str, ChangeCategory] = {}
    types_by_code: dict[str, CiType] = {}
    async with sessionmaker() as session, session.begin():
        for user_spec in SEED_USERS:
            user = await users.get_user_by_external_id(session, user_spec.external_id)
            if user is not None:
                users_by_external_id[user_spec.external_id] = user
        for code in ALL_ROOTS:
            category = await categories.get_category_by_code(session, code)
            if category is not None:
                categories_by_code[code] = category
        for code in SEED_CI_TYPE_CODES:
            ci_type = await ci_types.get_ci_type_by_code(session, code)
            if ci_type is not None:
                types_by_code[code] = ci_type

    for prefix in sorted(SEED_COMPANY_CATEGORIES):
        async with sessionmaker() as session, session.begin():
            await apply_company_scope(session, [], admin_scope=True)
            company = await companies.get_company_by_prefix(session, prefix)
            if company is None or company.status == CompanyStatus.ARCHIVED:
                report.add(f"spółka {prefix}: brak lub zarchiwizowana, pominięto", created=False)
                continue
            # The admin path for exactly this company: available categories are written
            # only there (RLS), and its CI and audit chain need it in the scope.
            await apply_company_scope(session, [company.id], admin_scope=True)
            added, notes = await _seed_company_categories(
                session,
                actor=actor,
                company_id=company.id,
                planned=SEED_COMPANY_CATEGORIES[prefix],
                categories_by_code=categories_by_code,
                users_by_external_id=users_by_external_id,
            )
            if added:
                report.add(f"kategorie w {prefix}: dodane {', '.join(added)}", created=True)
            for note in notes:
                report.add(f"kategorie w {prefix}: {note}", created=False)
            await _seed_company_ci(
                session,
                actor=actor,
                company=company,
                specs=SEED_CI[prefix],
                types_by_code=types_by_code,
                users_by_external_id=users_by_external_id,
                report=report,
            )
    return report


async def seed_all(
    sessionmaker: async_sessionmaker[AsyncSession], *, context: dict[str, object] | None = None
) -> SeedReport:
    """Everything of ``python -m app.cli seed`` (dev only), in the documented order.

    ``context``: who ran it (CLI operator), recorded in the dictionary entries."""
    report = SeedReport()
    parts = (
        await seed_identity(sessionmaker),
        await seed_dictionaries(sessionmaker, context=context),
        await seed_inventory(sessionmaker),
        await seed_changes(sessionmaker),
    )
    for part in parts:
        report.created += part.created
        report.lines.extend(part.lines)
    return report
