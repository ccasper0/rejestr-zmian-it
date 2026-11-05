"""``python -m app.cli seed``: idempotent sample identities, created through services (audited)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.cli import main
from app.config import get_settings
from app.models import Company, User
from app.permissions import Role
from app.services import memberships
from app.services.seed import (
    SEED_CATEGORY_CODES,
    SEED_CI_TYPE_CODES,
    SEED_COMPANIES,
    SEED_USERS,
    seed_all,
    seed_identity,
)
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import DEV_SECRET, DbUrls
from tests.factories import SYSTEM, scoped, verify

pytestmark = pytest.mark.db

EXPECTED_ROLES = {
    "dev-admin": {},
    "dev-editor": {"ALFA": {Role.EDITOR}, "BETA": {Role.EDITOR}, "GAMMA": {Role.EDITOR}},
    "dev-approver": {"ALFA": {Role.APPROVER}, "BETA": {Role.APPROVER}, "GAMMA": {Role.APPROVER}},
    "dev-auditor": {"ALFA": {Role.AUDITOR}, "BETA": {Role.AUDITOR}, "GAMMA": {Role.AUDITOR}},
    "dev-viewer": {"GAMMA": {Role.VIEWER}},
}


async def _audit_count(engine: AsyncEngine, company_ids: list[object]) -> int:
    async with scoped(engine, company_ids, global_read=True) as session:  # type: ignore[arg-type]
        return int(
            (
                await session.execute(
                    text(
                        "SELECT count(*) FROM audit_log "
                        "WHERE company_id IS NULL OR company_id = ANY (app_company_ids())"
                    )
                )
            ).scalar_one()
        )


async def test_seed_is_idempotent_and_audited(rw_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(rw_engine, expire_on_commit=False)
    await seed_identity(factory)
    second = await seed_identity(factory)
    assert second.created == 0  # nothing new the second time

    async with scoped(rw_engine, admin_scope=True) as session:
        companies = {
            c.prefix: c
            for c in (
                await session.execute(
                    select(Company).where(Company.prefix.in_(["ALFA", "BETA", "GAMMA"]))
                )
            ).scalars()
        }
        users = {
            u.external_id: u
            for u in (
                await session.execute(select(User).where(User.external_id.like("dev-%")))
            ).scalars()
        }
        roles = {ext: await memberships.roles_by_company(session, u.id) for ext, u in users.items()}
    assert set(companies) == {"ALFA", "BETA", "GAMMA"}
    assert companies["ALFA"].is_ksc_entity is True
    assert companies["BETA"].is_ksc_entity is False
    assert companies["ALFA"].default_approver_id == users["dev-approver"].id
    assert set(users) >= set(EXPECTED_ROLES)
    assert users["dev-admin"].is_app_admin is True
    assert not any(users[e].is_app_admin for e in EXPECTED_ROLES if e != "dev-admin")
    by_id = {c.id: p for p, c in companies.items()}
    for external_id, expected in EXPECTED_ROLES.items():
        actual = {by_id[cid]: set(r) for cid, r in roles[external_id].items()}
        assert actual == expected, external_id
    assert len(SEED_USERS) == 5
    assert len(SEED_COMPANIES) == 3

    ids = [c.id for c in companies.values()]
    before = await _audit_count(rw_engine, ids)
    await seed_identity(factory)
    assert await _audit_count(rw_engine, ids) == before  # idempotent: no new audit entries

    # Audited as the system actor; chains intact.
    async with scoped(rw_engine, ids, global_read=True) as session:
        actors = (
            await session.execute(
                text(
                    "SELECT DISTINCT actor_display, actor_id IS NULL AS system FROM audit_log "
                    "WHERE entity_id = ANY (:ids)"
                ),
                {"ids": [*ids, *(u.id for u in users.values() if u.external_id in EXPECTED_ROLES)]},
            )
        ).all()
    assert {(a.actor_display, a.system) for a in actors} == {("system", True)}
    assert (await verify(rw_engine, None)).ok
    for cid in ids:
        assert (await verify(rw_engine, cid)).ok


def _cli_env(monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, app_env: str) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("AUTH_MODE", "dev" if app_env == "dev" else "local")
    monkeypatch.setenv("DEV_AUTH_SECRET", DEV_SECRET)
    monkeypatch.setenv("AUTH_JWT_SECRET", LOCAL_SECRET)
    monkeypatch.setenv("DATABASE_URL", db_urls.rw)
    get_settings.cache_clear()


def test_cli_seed(
    monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, capsys: pytest.CaptureFixture[str]
) -> None:
    _cli_env(monkeypatch, db_urls, "dev")
    try:
        assert main(["seed"]) == 0
    finally:
        get_settings.cache_clear()
    out = capsys.readouterr().out
    assert "ALFA" in out
    assert "dev-editor" in out


def test_cli_seed_refused_in_production(
    monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, capsys: pytest.CaptureFixture[str]
) -> None:
    _cli_env(monkeypatch, db_urls, "prod")
    try:
        assert main(["seed"]) == 1
    finally:
        get_settings.cache_clear()
    assert "APP_ENV=prod" in capsys.readouterr().err


# --------------------------------------------------------------------------- stage 3: dictionaries


async def _seeded_inventory(engine: AsyncEngine) -> dict[str, Any]:
    from app.models import ChangeCategory, CiType, CompanyCategory, ConfigurationItem

    async with scoped(engine, admin_scope=True) as session:
        companies = {
            c.prefix: c.id
            for c in (
                await session.execute(
                    select(Company).where(Company.prefix.in_(["ALFA", "BETA", "GAMMA"]))
                )
            ).scalars()
        }
    async with scoped(engine, list(companies.values()), admin_scope=True) as session:
        categories = {
            c.code: c
            for c in (
                await session.execute(
                    select(ChangeCategory).where(ChangeCategory.code.in_(SEED_CATEGORY_CODES))
                )
            ).scalars()
        }
        types = {
            t.code: t
            for t in (
                await session.execute(select(CiType).where(CiType.code.in_(SEED_CI_TYPE_CODES)))
            ).scalars()
        }
        by_id = {c.id: c.code for c in categories.values()}
        available: dict[str, dict[str, Any]] = {p: {} for p in companies}
        prefix_of = {cid: p for p, cid in companies.items()}
        for link in (
            await session.execute(
                select(CompanyCategory).where(
                    CompanyCategory.company_id.in_(list(companies.values()))
                )
            )
        ).scalars():
            if link.category_id in by_id:
                available[prefix_of[link.company_id]][by_id[link.category_id]] = (
                    link.approver_override_id
                )
        items = (
            await session.execute(
                select(ConfigurationItem).where(
                    ConfigurationItem.company_id.in_(list(companies.values()))
                )
            )
        ).scalars()
        ci = {(prefix_of[i.company_id], i.identifier): i for i in items}
    return {
        "companies": companies,
        "categories": categories,
        "types": types,
        "available": available,
        "ci": ci,
    }


async def test_seed_dictionaries_and_inventory(rw_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(rw_engine, expire_on_commit=False)
    await seed_all(factory)
    second = await seed_all(factory)
    assert second.created == 0

    data = await _seeded_inventory(rw_engine)
    categories, types = data["categories"], data["types"]
    # §13: ten categories with subcategories, two levels.
    roots = {c for c, v in categories.items() if v.parent_id is None}
    assert roots == {"ACC", "NET", "FW", "SRV", "PATCH", "BKP", "GPO", "APP", "SEC", "OT"}
    for code, category in categories.items():
        if category.parent_id is not None:
            parent = next(c for c in categories.values() if c.id == category.parent_id)
            assert code.startswith(parent.code + "-"), code
            assert parent.parent_id is None
    assert {
        r: sum(1 for c in categories.values() if c.parent_id == categories[r].id) for r in roots
    } == {
        "ACC": 5,
        "NET": 3,
        "FW": 3,
        "SRV": 4,
        "PATCH": 3,
        "BKP": 3,
        "GPO": 3,
        "APP": 3,
        "SEC": 3,
        "OT": 2,
    }
    # ACC: standard (no approval) except privileged accounts (ADR 0011 §3).
    assert categories["ACC"].requires_approval is False
    assert categories["ACC-PRIV"].requires_approval is True
    assert categories["ACC-PRIV"].default_risk == "high"
    assert {
        c.requires_approval
        for k, c in categories.items()
        if k.startswith("ACC-") and k != "ACC-PRIV"
    } == {False}
    assert all(c.requires_approval for k, c in categories.items() if not k.startswith("ACC"))
    assert categories["OT"].default_risk == "high"
    assert categories["OT"].requires_ci_owner_consent is True  # ADR 0012 §5
    assert not any(c.requires_ci_owner_consent for k, c in categories.items() if k != "OT")
    # §4.1 CI types with Polish names.
    assert set(types) == set(SEED_CI_TYPE_CODES)
    assert types["network_device"].name == "Urządzenie sieciowe"

    available = data["available"]
    assert set(available["ALFA"]) == roots
    assert set(available["BETA"]) == roots - {"OT"}
    assert set(available["GAMMA"]) == roots - {"OT"}
    approver = await _user_id(rw_engine, "dev-approver")
    assert available["ALFA"]["FW"] == approver
    assert {v for k, v in available["ALFA"].items() if k != "FW"} == {None}

    ci = data["ci"]
    per_company = {p: sum(1 for (cp, _) in ci if cp == p) for p in ("ALFA", "BETA", "GAMMA")}
    assert 28 <= sum(per_company.values()) <= 34
    assert all(n >= 8 for n in per_company.values())
    inactive = {key for key, item in ci.items() if not item.is_active}
    assert len(inactive) >= 3
    used_types = {item.ci_type_id for item in ci.values()}
    assert used_types == {t.id for t in types.values()}  # every type is used somewhere
    assert ci[("ALFA", "FW-01")].owner_user_id == approver

    # Idempotent: no new audit entries; chains intact; everything by the system actor.
    ids = list(data["companies"].values())
    before = await _audit_count(rw_engine, ids)
    await seed_all(factory)
    assert await _audit_count(rw_engine, ids) == before
    assert (await verify(rw_engine, None)).ok
    for cid in ids:
        assert (await verify(rw_engine, cid)).ok
    async with scoped(rw_engine, ids, global_read=True) as session:
        kinds = (
            await session.execute(
                text(
                    "SELECT DISTINCT entity_type, action, actor_display FROM audit_log "
                    "WHERE entity_id = ANY (:ids)"
                ),
                {"ids": [*(c.id for c in categories.values()), *(i.id for i in ci.values())]},
            )
        ).all()
    assert {k.actor_display for k in kinds} == {"system"}
    assert {(k.entity_type, k.action) for k in kinds} == {
        ("category", "create"),
        ("ci", "create"),
        ("ci", "deactivate"),
    }


async def _user_id(engine: AsyncEngine, external_id: str) -> Any:
    async with scoped(engine) as session:
        return (
            await session.execute(select(User.id).where(User.external_id == external_id))
        ).scalar_one()


def test_cli_seed_dictionaries_also_in_production(
    monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, capsys: pytest.CaptureFixture[str]
) -> None:
    """Reference dictionaries (not sample data) may be loaded in production."""
    _cli_env(monkeypatch, db_urls, "prod")
    try:
        assert main(["seed-dictionaries"]) == 0
    finally:
        get_settings.cache_clear()
    out = capsys.readouterr().out
    assert "ACC" in out
    assert "network_device" in out


def test_cli_seed_dictionaries_database_error_is_exit_code_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app import cli
    from tests.conftest import make_settings

    unreachable = "postgresql+asyncpg://app_rw:x@127.0.0.1:1/none"
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings(database_url=unreachable))
    assert main(["seed-dictionaries"]) == 1
    assert "nie udało się załadować słowników" in capsys.readouterr().err


# --------------------------------------------------------------------------- stage 3 review


async def test_reseed_does_not_restore_withdrawn_categories(rw_engine: AsyncEngine) -> None:
    """Once a company has categories they belong to the admin: a later seed neither
    restores a withdrawn category nor fails."""
    from app.services import company_categories

    factory = async_sessionmaker(rw_engine, expire_on_commit=False)
    await seed_all(factory)
    alfa = (await _seeded_inventory(rw_engine))["companies"]["ALFA"]
    async with scoped(rw_engine, [alfa], admin_scope=True) as session:
        original = await company_categories.list_company_categories(session, alfa)
        await company_categories.set_company_categories(
            session,
            actor=SYSTEM,
            company_id=alfa,
            assignments=[
                company_categories.Assignment(a.category.id, a.approver_override_id)
                for a in original
                if a.category.code != "OT"
            ],
        )
    try:
        report = await seed_all(factory)
        assert report.created == 0
        assert "kategorie w ALFA: już ustawione, seed ich nie zmienia" in report.lines
        assert "OT" not in (await _seeded_inventory(rw_engine))["available"]["ALFA"]
    finally:
        async with scoped(rw_engine, [alfa], admin_scope=True) as session:
            await company_categories.set_company_categories(
                session,
                actor=SYSTEM,
                company_id=alfa,
                assignments=[
                    company_categories.Assignment(a.category.id, a.approver_override_id)
                    for a in original
                ],
            )


async def test_seed_skips_inactive_and_ineligible_entries(rw_engine: AsyncEngine) -> None:
    """Inactive dictionary entries, an override without the approver role and an owner
    outside the company are skipped with a note - never a traceback."""
    from app.services import categories as categories_service
    from app.services import ci_types as ci_types_service
    from app.services.seed import SeedCi, SeedReport, _seed_company_categories, _seed_company_ci
    from tests.factories import grant, make_category, make_ci_type, make_company, make_user

    company = await make_company(rw_engine)
    editor = await make_user(rw_engine)
    outsider = await make_user(rw_engine)
    await grant(rw_engine, company, editor, Role.EDITOR)
    active = await make_category(rw_engine)
    inactive = await make_category(rw_engine)
    ci_type = await make_ci_type(rw_engine)
    off_type = await make_ci_type(rw_engine)
    async with scoped(rw_engine, admin_scope=True) as session:
        inactive = await categories_service.update_category(
            session, actor=SYSTEM, category_id=inactive.id, changes={"is_active": False}
        )
        off_type = await ci_types_service.update_ci_type(
            session, actor=SYSTEM, ci_type_id=off_type.id, changes={"is_active": False}
        )
    users_map = {editor.external_id: editor, outsider.external_id: outsider}
    planned = {active.code: editor.external_id, inactive.code: None, "TST-BRAK": None}

    async with scoped(rw_engine, [company.id], admin_scope=True) as session:
        added, notes = await _seed_company_categories(
            session,
            actor=SYSTEM,
            company_id=company.id,
            planned=planned,
            categories_by_code={active.code: active, inactive.code: inactive},
            users_by_external_id=users_map,
        )
        again = await _seed_company_categories(
            session,
            actor=SYSTEM,
            company_id=company.id,
            planned=planned,
            categories_by_code={active.code: active},
            users_by_external_id=users_map,
        )
        report = SeedReport()
        await _seed_company_ci(
            session,
            actor=SYSTEM,
            company=company,
            specs=(
                SeedCi("OK-1", ci_type.code, "Z obcym właścicielem", owner=outsider.external_id),
                SeedCi("OFF-1", off_type.code, "Nieaktywny typ"),
            ),
            types_by_code={ci_type.code: ci_type, off_type.code: off_type},
            users_by_external_id=users_map,
            report=report,
        )
    assert added == [active.code]
    assert notes == [
        f"{active.code}: pominięto zatwierdzającego {editor.external_id} (brak roli approver)",
        f"pominięto {inactive.code} (brak w słowniku lub nieaktywna)",
        "pominięto TST-BRAK (brak w słowniku lub nieaktywna)",
    ]
    assert again == ([], ["już ustawione, seed ich nie zmienia"])
    prefix = company.prefix
    assert report.lines == [
        f"obiekt {prefix}/OK-1: bez właściciela {outsider.external_id} (nie jest członkiem)",
        f"obiekt {prefix}/OK-1: utworzony",
        f"obiekt {prefix}/OFF-1: pominięto (typ {off_type.code} brak lub nieaktywny)",
    ]
    assert report.created == 1


def test_cli_seed_problem_is_a_message_not_a_traceback(
    monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, capsys: pytest.CaptureFixture[str]
) -> None:
    from app import cli
    from app.errors import ProblemError

    async def failing(*_: Any, **__: Any) -> Any:
        raise ProblemError(status=422, code="ci.owner_not_member", detail="Właściciel obcy.")

    _cli_env(monkeypatch, db_urls, "dev")
    monkeypatch.setattr(cli, "seed_all", failing)
    try:
        assert main(["seed"]) == 1
    finally:
        get_settings.cache_clear()
    assert "Błąd: Właściciel obcy. (ci.owner_not_member)" in capsys.readouterr().err


def test_cli_seed_dictionaries_records_the_operator(
    monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, rw_engine: AsyncEngine
) -> None:
    """Allowed in production, so its entries say who ran it (like verify-audit)."""
    import asyncio

    from app import cli
    from app.domain.dictionaries import Risk
    from app.models import ChangeCategory, CiType
    from app.services import seed as seed_module
    from tests.factories import audit_entries, random_category_code, random_ci_type_code

    type_code, category_code = random_ci_type_code(), random_category_code()
    monkeypatch.setattr(seed_module, "SEED_CI_TYPES", ((type_code, "Typ z CLI"),))
    monkeypatch.setattr(
        seed_module,
        "SEED_CATEGORIES",
        (
            seed_module.SeedCategory(
                category_code, "Kategoria z CLI", True, Risk.LOW, (("SUB", "Pod", None, None),)
            ),
        ),
    )
    _cli_env(monkeypatch, db_urls, "prod")
    try:
        assert main(["seed-dictionaries"]) == 0
    finally:
        get_settings.cache_clear()

    async def entries() -> list[Any]:
        async with scoped(rw_engine) as session:
            ids = [
                (
                    await session.execute(select(CiType.id).where(CiType.code == type_code))
                ).scalar_one(),
                *(
                    await session.execute(
                        select(ChangeCategory.id)
                        .where(ChangeCategory.code.like(f"{category_code}%"))
                        .order_by(ChangeCategory.code)
                    )
                ).scalars(),
            ]
        return [e for i in ids for e in await audit_entries(rw_engine, i)]

    found = asyncio.run(entries())
    assert len(found) == 3
    expected = cli._operator("seed-dictionaries")
    assert set(expected) >= {"source", "command", "host"}
    assert [e.context for e in found] == [
        expected,
        expected,
        {**expected, "parent_code": category_code},
    ]


async def test_seed_changes_cover_the_register(rw_engine: AsyncEngine) -> None:
    """~40 sample changes through the services: every status, deviations, system
    auto-approvals, comments - audited with ``context.source = "seed"``; idempotent."""
    from datetime import UTC, datetime

    from app.domain.deviations import deviations
    from app.models import Change, ChangeComment
    from app.services.changes import change_subject
    from app.services.seed_changes import SEED_CHANGES

    factory = async_sessionmaker(rw_engine, expire_on_commit=False)
    await seed_all(factory)
    async with scoped(rw_engine, admin_scope=True) as session:
        companies = {
            c.prefix: c.id
            for c in (
                await session.execute(
                    select(Company).where(Company.prefix.in_(["ALFA", "BETA", "GAMMA"]))
                )
            ).scalars()
        }
    ids = list(companies.values())
    async with scoped(rw_engine, ids) as session:
        rows = list(
            (await session.execute(select(Change).where(Change.company_id.in_(ids)))).scalars()
        )
        comment_count = len(
            (
                await session.execute(
                    select(ChangeComment.id).where(ChangeComment.company_id.in_(ids))
                )
            ).all()
        )
    assert len(rows) == sum(len(v) for v in SEED_CHANGES.values()) == 40
    statuses = {c.status for c in rows}
    assert statuses == {
        "draft",
        "pending_approval",
        "approved",
        "implemented",
        "verified",
        "rejected",
        "rolled_back",
        "cancelled",
    }
    assert sum(1 for c in rows if c.status == "implemented") >= 2
    now = datetime.now(UTC)
    kinds = [d.kind.value for c in rows for d in deviations(change_subject(c), now=now)]
    assert "emergency_not_approved_in_24h" in kinds
    assert "approved_by_requester_or_assignee" not in kinds
    assert comment_count >= 8  # action comments + plain comments
    assert all(c.created_at < now for c in rows)
    approved = [c for c in rows if c.approved_at is not None]
    by_system = [c for c in approved if c.approved_by_id is None]
    assert len(by_system) >= 3  # standard changes approved by system
    assert {c.change_type for c in by_system} == {"standard"}
    approver = await _user_id(rw_engine, "dev-approver")
    assert {c.approved_by_id for c in approved if c.approved_by_id} == {approver}

    async with scoped(rw_engine, ids) as session:
        entries = (
            await session.execute(
                text(
                    "SELECT actor_id, context FROM audit_log WHERE company_id = ANY (:ids) "
                    "AND entity_type = 'change'"
                ),
                {"ids": ids},
            )
        ).all()
    assert entries
    assert all(e.context.get("source") == "seed" for e in entries)
    assert all("simulated_at" in e.context for e in entries)
    auto = [e for e in entries if e.context.get("auto_approved")]
    assert len(auto) >= 3
    assert {e.actor_id for e in auto} == {None}

    before = await _audit_count(rw_engine, ids)
    again = await seed_all(factory)
    assert again.created == 0
    assert await _audit_count(rw_engine, ids) == before
    for cid in ids:
        assert (await verify(rw_engine, cid)).ok
