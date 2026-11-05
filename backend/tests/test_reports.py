"""Report exports (CLAUDE.md §9, §12 Etap 7; ADR 0017).

- PDF with Polish text (pypdf), "Strona X z Y", ``data_sha256`` identical in the PDF footer,
  ``report_exports`` and ``audit_log`` (tests marked ``pdf`` need WeasyPrint + Pango);
- all 9 sections of the register report in order, appendix B optional;
- deviations computed on the seed data;
- CSV (BOM, separator, Polish letters, filters, formula injection);
- background generation (threshold), the worker re-checks the permission;
- numbering, RLS of multi-company rows, the row guard, tampered files.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import os
import re
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.db import set_current_user
from app.domain.canonical import canonical_json_bytes, sha256_hex
from app.domain.reports import (
    REPORT_NUMBER_PATTERN,
    ReportKind,
    format_report_number,
    register_tiles,
)
from app.main import create_app
from app.models import Company, ReportExport, User
from app.permissions import PERMISSIONS, Action, Role
from app.reports.csv_export import HEADER, register_csv
from app.services import changes as changes_service
from app.services import report_jobs
from app.services import reports as reports_service
from app.services.changes import db_now
from tests.conftest import TEST_STORAGE, DbUrls, make_settings
from tests.factories import (
    RecordingQueue,
    World,
    act,
    add_changes,
    audit_entries,
    auth,
    change_actor,
    client_for,
    grant,
    make_attachment,
    make_available,
    make_category,
    make_change,
    make_ci,
    make_company,
    make_report,
    make_user,
    ready_values,
    scoped,
    stub_pdf,
    verify,
)
from tests.test_api_auth import assert_problem
from tests.test_audit_log import owner_exec
from tests.test_audit_verify import tamper_last_hash

POLISH = "zażółć gęślą jaźń"
PERIOD = {"period_from": "2000-01-01T00:00:00Z", "period_to": "2100-01-01T00:00:00Z"}


class Capture:
    """A renderer that keeps the HTML (and returns a stand-in PDF)."""

    def __init__(self) -> None:
        self.html: list[str] = []

    def __call__(self, html: str) -> bytes:
        self.html.append(html)
        return stub_pdf(html)


def pdf_text(content: bytes) -> list[str]:
    from pypdf import PdfReader

    return [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]


async def export_entries(engine: AsyncEngine, report_id: UUID) -> list[Any]:
    return [e for e in await audit_entries(engine, report_id) if e.action == "export"]


# --------------------------------------------------------------------------- pure


def test_report_numbers() -> None:
    assert format_report_number("ALFA", 2026, 7) == "RAP-ALFA-2026-0007"
    assert format_report_number(None, 2026, 12345) == "RAP-2026-12345"
    assert REPORT_NUMBER_PATTERN.match("RAP-ALFA-2026-0007")
    assert REPORT_NUMBER_PATTERN.match("RAP-2026-0001")
    # A company prefix can never produce the multi-company form (no prefix segment).
    assert not REPORT_NUMBER_PATTERN.match("RAP-ALL-2026")
    with pytest.raises(ValueError, match="start at 1"):
        format_report_number("ALFA", 2026, 0)


def test_worker_permission_mirror_matches_the_matrix() -> None:
    """``report_jobs`` re-checks the permission in the worker with the matrix rows."""
    members = {Role.APPROVER, Role.EDITOR, Role.AUDITOR, Role.VIEWER}
    for kind, action in (
        ("register", Action.EXPORT_REGISTER),
        ("change_card", Action.EXPORT_CHANGE_CARD),
    ):
        expected = {r.value for r in PERMISSIONS[action] & members}
        assert report_jobs._KIND_ROLES[kind] == expected


def test_export_permissions_follow_section_5() -> None:
    assert PERMISSIONS[Action.EXPORT_REGISTER] == {Role.APP_ADMIN, Role.APPROVER, Role.AUDITOR}
    assert PERMISSIONS[Action.EXPORT_CHANGE_CARD] == {
        Role.APP_ADMIN,
        Role.APPROVER,
        Role.EDITOR,
        Role.AUDITOR,
    }


def _csv_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "company_prefix": "ALFA",
        "number": "CHG-ALFA-2026-0001",
        "title": POLISH,
        "category": "FW — Firewall",
        "subcategory": None,
        "change_type": "emergency",
        "risk": "high",
        "status": "implemented",
        "ci": ["FW-01", "SRV-02"],
        "requested_by": "Ewa Łęcka",
        "assignee": "Ewa Łęcka",
        "approver": "Jan Ąę",
        "approved_by": "system (automatycznie)",
        "approved_at": "2026-07-01T10:00:00.000000Z",
        "window_start": None,
        "window_end": None,
        "implemented_at": "2026-01-15T23:30:00.000000Z",
        "verifier": None,
        "verified_at": None,
        "deviations": ["implemented_not_verified"],
        "ticket_ref": "=HYPERLINK(1)",
        "requirement_ref": "ISO; A.8.32",
        "created_at": "2026-01-15T10:00:00.000000Z",
    }
    row.update(overrides)
    return row


def test_csv_format_bom_separator_polish_dates_and_formula_injection() -> None:
    content = register_csv({"changes": [_csv_row()]})
    assert content.startswith(b"\xef\xbb\xbf")
    lines = content.decode("utf-8-sig").split("\r\n")
    assert lines[0].split(";") == list(HEADER)
    assert lines[-1] == ""  # CRLF after the last row
    assert POLISH in lines[1]
    fields = next(iter(__import__("csv").reader([lines[1]], delimiter=";")))
    by_name = dict(zip(HEADER, fields, strict=True))
    assert by_name["Typ"] == "Awaryjna"
    assert by_name["Status"] == "Wdrożona"
    # Europe/Warsaw: winter UTC+1, summer UTC+2.
    assert by_name["Data wdrożenia"] == "16.01.2026 00:30"
    assert by_name["Data zatwierdzenia"] == "01.07.2026 12:00"
    assert by_name["Zgłoszenie"] == "'=HYPERLINK(1)"  # never evaluated by Excel
    assert by_name["Podstawa / wymóg"] == "ISO; A.8.32"  # quoted, separator kept
    assert by_name["Obiekty (CI)"] == "FW-01, SRV-02"
    assert by_name["Odstępstwa"] == "bez weryfikacji"


def test_register_tiles() -> None:
    from dataclasses import dataclass

    from app.domain.changes import ChangeStatus, ChangeType

    @dataclass
    class Row:
        status: ChangeStatus
        change_type: ChangeType | None
        approved_at: datetime | None
        implemented_at: datetime | None

    t = datetime(2026, 1, 1, tzinfo=UTC)
    tiles = register_tiles(
        [
            Row(ChangeStatus.VERIFIED, ChangeType.NORMAL, t, t + timedelta(hours=1)),
            Row(ChangeStatus.IMPLEMENTED, ChangeType.EMERGENCY, None, t),
            Row(ChangeStatus.VERIFIED, ChangeType.EMERGENCY, t + timedelta(hours=2), t),
            Row(ChangeStatus.DRAFT, None, None, None),
        ]
    )
    assert (tiles.total, tiles.implemented, tiles.approved_before_implementation) == (4, 3, 1)
    assert (tiles.emergency, tiles.not_verified) == (2, 1)


# --------------------------------------------------------------------------- fixtures


async def _app(db_urls: DbUrls, **settings: Any) -> FastAPI:
    from app.reports.render import weasyprint_available

    application = create_app(make_settings(database_url=db_urls.rw, **settings))
    application.state.report_queue = RecordingQueue()
    if not weasyprint_available():
        application.state.pdf_renderer = stub_pdf
    return application


@pytest.fixture
async def world(world: World, rw_engine: AsyncEngine) -> World:
    return await add_changes(rw_engine, world)


@pytest.fixture
async def small_app(db_urls: DbUrls) -> AsyncIterator[FastAPI]:
    """Background generation from 2 changes on (``REPORT_ASYNC_THRESHOLD=1``)."""
    application = await _app(db_urls, report_async_threshold=1)
    yield application
    await application.state.db.dispose()


@pytest.fixture
async def small_api(small_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with client_for(small_app) as client:
        yield client


async def _polish_world(engine: AsyncEngine) -> tuple[Company, User, Any]:
    """A company, an auditor and an implemented change with Polish text everywhere."""
    company = await make_company(engine, name=f"Spółka {POLISH} {uuid4().hex[:6]}")
    editor = await make_user(engine, name="Łukasz Żółkiewski")
    approver = await make_user(engine, name="Ścibor Ćwikła")
    auditor = await make_user(engine, name="Agnieszka Źrebięcka")
    await grant(engine, company, editor, Role.EDITOR)
    await grant(engine, company, approver, Role.APPROVER)
    await grant(engine, company, auditor, Role.AUDITOR)
    category = await make_category(engine, name=f"Kategoria {POLISH}")
    await make_available(engine, company, category)
    ci = await make_ci(engine, company, (await _ci_type(engine)), name=f"Zapora {POLISH}")
    values = ready_values(
        category=category, ci=[ci], assignee=editor, approver=approver, title=POLISH
    )
    change = await make_change(engine, company, editor, Role.EDITOR, values=values)
    for user, action, role in (
        (editor, "submit", Role.EDITOR),
        (approver, "approve", Role.APPROVER),
        (editor, "implement", Role.EDITOR),
    ):
        change = await act(engine, company, change, user, action, role)
    await make_attachment(
        engine, company, change, editor, Role.EDITOR, filename="dowód-wdrożenia.txt"
    )
    return company, auditor, change


async def _ci_type(engine: AsyncEngine) -> Any:
    from tests.factories import make_ci_type

    return await make_ci_type(engine)


# --------------------------------------------------------------------------- PDF (WeasyPrint)


@pytest.mark.db
@pytest.mark.pdf
async def test_pdf_with_polish_text_page_numbers_and_the_same_hash_everywhere(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    company, auditor, change = await _polish_world(rw_engine)
    created = await api.post(
        "/api/v1/reports",
        json={
            "kind": "register",
            "company_id": str(company.id),
            "include_audit_trail": True,
            **PERIOD,
        },
        headers=auth(auditor),
    )
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["status"] == "done"
    assert re.fullmatch(rf"RAP-{company.prefix}-\d{{4}}-0001", report["number"])

    downloaded = await api.get(report["download_url"], headers=auth(auditor))
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.headers["content-type"] == "application/pdf"
    assert downloaded.content.startswith(b"%PDF")
    pages = pdf_text(downloaded.content)
    whole = "\n".join(pages)
    assert POLISH in whole  # exactly this text, extracted by pypdf
    assert "Łukasz Żółkiewski" in whole
    for index, page in enumerate(pages, start=1):
        assert f"Strona {index} z {len(pages)}" in page
        assert report["number"] in page
        assert report["data_sha256"] in page.replace("\n", "")
    for heading in (
        "Raport rejestru zmian",
        "Podsumowanie",
        "Zakres i zastosowane filtry",
        "Rejestr zmian",
        "Odstępstwa",
        "Załącznik A",
        "Załącznik B",
        "Weryfikacja łańcucha audytu",
        "Sporządził",
        "Zatwierdził (właściciel procesu)",
    ):
        assert heading in whole, heading
    assert change.number in whole

    # data_sha256: PDF footer == report_exports == audit_log (every entry of the report).
    async with scoped(rw_engine, [company.id]) as session:
        row = (
            await session.execute(select(ReportExport).where(ReportExport.id == report["id"]))
        ).scalar_one()
    assert row.data_sha256 == report["data_sha256"] == downloaded.headers["x-data-sha256"]
    entries = await export_entries(rw_engine, UUID(report["id"]))
    assert {e.context["event"] for e in entries} == {"generated", "downloaded"}
    assert {e.context["data_sha256"] for e in entries} == {row.data_sha256}
    assert {e.context["number"] for e in entries} == {row.number}
    assert {e.company_id for e in entries} == {company.id}
    assert (await verify(rw_engine, company.id)).ok


@pytest.mark.db
@pytest.mark.pdf
async def test_change_card_pdf_has_fields_trail_and_attachments(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    company, auditor, change = await _polish_world(rw_engine)
    created = await api.post(
        "/api/v1/reports",
        json={"kind": "change_card", "company_id": str(company.id), "change_id": str(change.id)},
        headers=auth(auditor),
    )
    assert created.status_code == 201, created.text
    pdf = await api.get(created.json()["download_url"], headers=auth(auditor))
    pages = pdf_text(pdf.content)
    whole = "\n".join(pages).replace("\n", " ")
    assert f"Strona 1 z {len(pages)}" in pages[0]
    for expected in (
        change.number,
        POLISH,
        "Plan wdrożenia",
        "Oś czasu statusów",
        "Ścieżka audytu",
        "dowód-wdrożenia.txt",
        "Ścibor Ćwikła",
        "Wdrożona",
    ):
        assert expected in whole, expected
    # Readable diffs: names, not raw ids (ADR 0015 §7).
    assert str(change.assignee_id) not in whole
    assert str(change.category_id) not in whole


# --------------------------------------------------------------------------- HTML / data


@pytest.mark.db
async def test_register_report_has_all_sections_in_order(
    rw_engine: AsyncEngine, world: World
) -> None:
    sections = [
        "<h1>Raport rejestru zmian</h1>",
        "<h2>Podsumowanie</h2>",
        "<h2>Zakres i zastosowane filtry</h2>",
        "<h2>Rejestr zmian</h2>",
        "<h2>Odstępstwa</h2>",
        "<h2>Załącznik A.",
        "Załącznik B.",
        "<h2>Weryfikacja łańcucha audytu w chwili generowania</h2>",
        "Zatwierdził (właściciel procesu)",
    ]
    for include in (True, False):
        capture = Capture()
        await make_report(
            rw_engine,
            [world.a],
            world.auditor,
            {world.a.id: {Role.AUDITOR}},
            include_audit_trail=include,
            renderer=capture,
        )
        (html,) = capture.html
        wanted = sections if include else [s for s in sections if "Załącznik B" not in s]
        positions = [html.find(s) for s in wanted]
        assert all(p >= 0 for p in positions), list(zip(wanted, positions, strict=True))
        assert positions == sorted(positions)
        assert ("Załącznik B." in html) is include
        assert "@page" in html
        assert 'counter(page) " z " counter(pages)' in html
        assert "IBMPlexSans-Regular.woff" in html


@pytest.mark.db
async def test_data_hash_is_the_canonical_hash_of_the_rendered_data(
    rw_engine: AsyncEngine, world: World
) -> None:
    """The footer hash is sha256(canonical_json(data)) - the serialization of the audit
    chain - and the stored row and the audit entry carry the same value."""
    capture = Capture()
    report = await make_report(
        rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}}, renderer=capture
    )
    assert report.data_sha256 is not None
    assert f"sha256 danych: {report.data_sha256}" in capture.html[0]
    (entry,) = await export_entries(rw_engine, report.id)
    assert entry.context["data_sha256"] == report.data_sha256
    assert entry.context["event"] == "generated"
    assert entry.context["chain"]["ok"] is True
    # Rebuilding the data as of the same moment gives the same hash.
    async with scoped(rw_engine, [world.a.id]) as session:
        await set_current_user(session, world.auditor.id)
        data = await reports_service.build_data(
            session,
            report=report,
            generated_by=world.auditor.display_name,
            now=report.completed_at,  # type: ignore[arg-type]
            max_changes=5000,
        )
    data["chain_verifications"] = [
        {
            **v,
            "head_seq": entry.context["chain"]["head_seq"],
            "head_hash": entry.context["chain"]["head_hash"],
            "checked": entry.context["chain"]["checked"],
        }
        for v in data["chain_verifications"]
    ]
    assert sha256_hex(canonical_json_bytes(data)) == report.data_sha256


@pytest.mark.db
async def test_change_card_shows_correction_links_both_ways(
    rw_engine: AsyncEngine, world: World
) -> None:
    """ADR 0021: "Korekta zmiany" on the correction, "Skorygowana przez" on the original;
    both are part of the hashed data (data_sha256)."""
    original = world.implemented_a
    assert original is not None
    async with scoped(rw_engine, [world.a.id]) as session:
        correction = await changes_service.create_change(
            session,
            actor=change_actor(world.editor, world.a, Role.EDITOR),
            company=world.a,
            values={"title": "Korekta"},
            supersedes_change_id=original.id,
        )
    cards = {}
    for change in (original, correction):
        capture = Capture()
        await make_report(
            rw_engine,
            [world.a],
            world.auditor,
            {world.a.id: {Role.AUDITOR}},
            kind="change_card",
            change=change,
            renderer=capture,
        )
        cards[change.id] = capture.html[0]
    original_html, correction_html = cards[original.id], cards[correction.id]
    assert "Skorygowana przez" in original_html
    assert correction.number in original_html
    assert "Korekta zmiany" not in original_html
    assert "Korekta zmiany" in correction_html
    assert original.number in correction_html
    assert "Skorygowana przez" not in correction_html

    report = await make_report(
        rw_engine,
        [world.a],
        world.auditor,
        {world.a.id: {Role.AUDITOR}},
        kind="change_card",
        change=original,
    )
    async with scoped(rw_engine, [world.a.id]) as session:
        await set_current_user(session, world.auditor.id)
        data = await reports_service.build_data(
            session,
            report=report,
            generated_by=world.auditor.display_name,
            now=await db_now(session),
            max_changes=5000,
        )
    assert data["change"]["supersedes_number"] is None
    assert data["change"]["superseded_by"] == [{"number": correction.number, "status": "draft"}]


# --------------------------------------------------------------------------- deviations (seed)


@pytest.mark.db
async def test_deviations_on_the_seed_data(rw_engine: AsyncEngine) -> None:
    """``python -m app.cli seed``: 40 changes, of which 3 emergency (one not approved at
    all, one approved after 24 h), 6 implemented without verification, 2 rolled back, none
    outside the window, none approved by the author (ADR 0013 §9)."""
    from app.services.seed import seed_all

    await seed_all(async_sessionmaker(rw_engine, expire_on_commit=False))
    async with scoped(rw_engine, admin_scope=True) as session:
        companies = list(
            (
                await session.execute(
                    select(Company)
                    .where(Company.prefix.in_(["ALFA", "BETA", "GAMMA"]))
                    .order_by(Company.prefix)
                )
            ).scalars()
        )
        auditor = (
            await session.execute(select(User).where(User.external_id == "dev-auditor"))
        ).scalar_one()
    capture = Capture()
    report = await make_report(
        rw_engine,
        companies,
        auditor,
        {c.id: {Role.AUDITOR} for c in companies},
        aggregate=True,
        renderer=capture,
    )
    assert report.company_id is None
    assert re.fullmatch(r"RAP-\d{4}-\d{4,}", report.number)
    async with scoped(rw_engine, [c.id for c in companies]) as session:
        await set_current_user(session, auditor.id)
        data = await reports_service.build_register_data(
            session,
            report=report,
            companies=companies,
            generated_by=auditor.display_name,
            now=await db_now(session),
            max_changes=5000,
        )
    devs = {d["kind"]: d["changes"] for d in data["deviations"]}
    per_company = {
        kind: sorted(c["number"].split("-")[1] for c in rows) for kind, rows in devs.items()
    }
    assert per_company == {
        "emergency_not_approved_in_24h": ["ALFA", "BETA"],
        "implemented_not_verified": ["ALFA", "ALFA", "ALFA", "BETA", "GAMMA", "GAMMA"],
        "implemented_outside_window": [],
        "rolled_back": ["ALFA", "BETA"],
        "approved_by_requester_or_assignee": [],
    }
    titles = {c["title"] for c in devs["emergency_not_approved_in_24h"]}
    assert titles == {
        "Wyłączenie podatnego protokołu SMBv1",
        "Poprawka bezpieczeństwa serwera WWW",
    }
    async with scoped(rw_engine, [c.id for c in companies]) as session:
        counts = (
            await session.execute(
                text(
                    "SELECT count(*) AS total, count(implemented_at) AS implemented, "
                    "count(*) FILTER (WHERE approved_at <= implemented_at) AS approved_first "
                    "FROM changes WHERE company_id = ANY (:ids)"
                ),
                {"ids": [c.id for c in companies]},
            )
        ).one()
    assert data["tiles"] == {
        "total": 40,
        "implemented": counts.implemented,
        "approved_before_implementation": counts.approved_first,
        "emergency": 3,
        "not_verified": 6,
    }
    assert counts.total == 40
    assert [v["prefix"] for v in data["chain_verifications"]] == ["ALFA", "BETA", "GAMMA"]
    assert all(v["ok"] for v in data["chain_verifications"])
    html = capture.html[0]
    assert "Zmiany awaryjne bez zatwierdzenia w ciągu 24 h" in html
    assert "BŁĄD KRYTYCZNY" not in html  # no critical deviation on the seed data
    # The multi-company report is recorded in the chain of EVERY company of the report.
    entries = await export_entries(rw_engine, report.id)
    assert {e.company_id for e in entries} == {c.id for c in companies}
    assert {e.context["data_sha256"] for e in entries} == {report.data_sha256}


@pytest.mark.db
async def test_critical_deviation_is_highlighted(rw_engine: AsyncEngine, world: World) -> None:
    """Approval by the requester cannot be stored (CHECK), so the template is rendered on
    data where it occurred (the section must stand out when it ever happens)."""
    from app.reports.render import render_html

    capture = Capture()
    await make_report(
        rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}}, renderer=capture
    )
    async with scoped(rw_engine, [world.a.id]) as session:
        report = (
            await session.execute(
                select(ReportExport)
                .where(ReportExport.company_id == world.a.id)
                .order_by(ReportExport.created_at.desc())
                .limit(1)
            )
        ).scalar_one()
        data = await reports_service.build_register_data(
            session,
            report=report,
            companies=[world.a],
            generated_by="x",
            now=await db_now(session),
            max_changes=5000,
        )
    from app.domain.canonical import to_json_value

    plain: Any = to_json_value(data)
    for section in plain["deviations"]:
        if section["critical"]:
            section["changes"] = [{"number": "CHG-X-2026-0001", "title": "t", "detail": "d"}]
    html = render_html("register", plain, number="RAP-X-2026-0001", data_sha256="0" * 64)
    assert 'class="critical"' in html
    assert "BŁĄD KRYTYCZNY" in html


# --------------------------------------------------------------------------- CSV


@pytest.mark.db
async def test_csv_export_filters_bom_and_audit(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    company, auditor, change = await _polish_world(rw_engine)
    url = f"/api/v1/companies/{company.id}/changes/export.csv"
    all_rows = await api.get(url, headers=auth(auditor))
    assert all_rows.status_code == 200, all_rows.text
    assert all_rows.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in all_rows.headers["content-disposition"]
    assert all_rows.content.startswith(b"\xef\xbb\xbf")
    lines = all_rows.content.decode("utf-8-sig").splitlines()
    assert lines[0].split(";") == list(HEADER)
    assert len(lines) == 2
    assert POLISH in lines[1]
    assert change.number in lines[1]

    filtered = await api.get(url, params={"status": "draft"}, headers=auth(auditor))
    assert filtered.content.decode("utf-8-sig").splitlines() == [";".join(HEADER)]
    bad = await api.get(url, params={"approved_by": "nikt"}, headers=auth(auditor))
    assert_problem(bad, 422, "change.invalid_filter")

    number = all_rows.headers["x-report-number"]
    report_id = UUID(all_rows.headers["x-report-id"])
    assert re.fullmatch(rf"RAP-{company.prefix}-\d{{4}}-\d{{4}}", number)
    (entry,) = await export_entries(rw_engine, report_id)
    assert entry.context["format"] == "csv"
    assert entry.context["data_sha256"] == all_rows.headers["x-data-sha256"]
    # Stored: the same bytes again from the report list, and that download is audited.
    again = await api.get(f"/api/v1/reports/{report_id}/download", headers=auth(auditor))
    assert again.content == all_rows.content
    events = [e.context["event"] for e in await export_entries(rw_engine, report_id)]
    assert events == ["generated", "downloaded"]


# --------------------------------------------------------------------------- background


@pytest.mark.db
async def test_large_report_is_generated_in_the_background(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    body = {"kind": "register", "company_id": str(world.a.id), **PERIOD}
    created = await small_api.post("/api/v1/reports", json=body, headers=auth(world.auditor))
    assert created.status_code == 202, created.text
    report = created.json()
    assert report["status"] == "pending"
    assert report["download_url"] is None
    (job,) = small_app.state.report_queue.jobs
    assert job["report_id"] == report["id"]
    assert job["company_ids"] == [str(world.a.id)]

    status = await small_api.get(f"/api/v1/reports/{report['id']}", headers=auth(world.auditor))
    assert status.json()["status"] == "pending"
    early = await small_api.get(
        f"/api/v1/reports/{report['id']}/download", headers=auth(world.auditor)
    )
    assert_problem(early, 409, "report.not_ready")

    capture = Capture()
    outcome = await report_jobs.run(
        async_sessionmaker(rw_engine, expire_on_commit=False),
        report_id=UUID(job["report_id"]),
        user_id=UUID(job["user_id"]),
        company_ids=[UUID(c) for c in job["company_ids"]],
        renderer=capture,
        storage_root=TEST_STORAGE,
        max_changes=5000,
    )
    assert outcome == "done"
    done = (
        await small_api.get(f"/api/v1/reports/{report['id']}", headers=auth(world.auditor))
    ).json()
    assert done["status"] == "done"
    assert done["data_sha256"] in capture.html[0]
    entries = await export_entries(rw_engine, UUID(report["id"]))
    assert [e.context["event"] for e in entries] == ["requested", "generated"]
    assert entries[1].context["source"] == "worker"
    assert entries[1].actor_id == world.auditor.id
    # A repeated job does nothing.
    again = await report_jobs.run(
        async_sessionmaker(rw_engine, expire_on_commit=False),
        report_id=UUID(job["report_id"]),
        user_id=UUID(job["user_id"]),
        company_ids=[UUID(c) for c in job["company_ids"]],
        renderer=capture,
        storage_root=TEST_STORAGE,
        max_changes=5000,
    )
    assert again == "skipped"


@pytest.mark.db
async def test_worker_rechecks_the_permission(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    auditor = await make_user(rw_engine)
    await grant(rw_engine, world.a, auditor, Role.AUDITOR)
    body = {"kind": "register", "company_id": str(world.a.id), **PERIOD}
    created = await small_api.post("/api/v1/reports", json=body, headers=auth(auditor))
    assert created.status_code == 202, created.text
    await grant(rw_engine, world.a, auditor)  # all roles revoked before the job runs
    job = small_app.state.report_queue.jobs[-1]
    outcome = await report_jobs.run(
        async_sessionmaker(rw_engine, expire_on_commit=False),
        report_id=UUID(job["report_id"]),
        user_id=UUID(job["user_id"]),
        company_ids=[UUID(c) for c in job["company_ids"]],
        renderer=stub_pdf,
        storage_root=TEST_STORAGE,
        max_changes=5000,
    )
    assert outcome == "failed"
    async with scoped(rw_engine, [world.a.id]) as session:
        row = (
            await session.execute(
                select(ReportExport).where(ReportExport.id == UUID(job["report_id"]))
            )
        ).scalar_one()
    assert row.status == "failed"
    assert row.error == report_jobs.NO_PERMISSION
    assert row.storage_key is None
    events = [e.context["event"] for e in await export_entries(rw_engine, row.id)]
    assert events == ["requested", "failed"]


@pytest.mark.db
async def test_a_job_retries_until_the_row_is_visible(monkeypatch: pytest.MonkeyPatch) -> None:
    from arq import Retry

    from app import worker

    async def invisible(*_: Any, **__: Any) -> str:
        return "not_visible"

    monkeypatch.setattr(report_jobs, "run", invisible)
    job = {"report_id": str(uuid4()), "user_id": str(uuid4()), "company_ids": []}
    with pytest.raises(Retry):
        await worker.generate_report({"db": SimpleNamespace(sessionmaker=None), "job_try": 1}, job)
    last = {"db": SimpleNamespace(sessionmaker=None), "job_try": worker.REPORT_ROW_RETRIES}
    assert await worker.generate_report(last, job) == "not_visible"


def test_only_the_report_job_has_the_long_timeout_and_retries() -> None:
    from arq.worker import Function

    from app import worker

    functions = worker.WorkerSettings.functions
    (report_job,) = [f for f in functions if isinstance(f, Function)]
    assert report_job.coroutine is worker.generate_report
    assert report_job.name == "generate_report"
    assert report_job.timeout_s == worker.REPORT_JOB_TIMEOUT_SECONDS
    assert report_job.max_tries == worker.REPORT_ROW_RETRIES
    # No global job_timeout / max_tries: other functions keep arq's defaults.
    assert not hasattr(worker.WorkerSettings, "job_timeout")
    assert not hasattr(worker.WorkerSettings, "max_tries")
    crons = {c.name: c for c in worker.WorkerSettings.cron_jobs}
    assert "cron:report_maintenance" in crons
    assert worker.REPORT_STALE_AFTER.total_seconds() > worker.REPORT_JOB_TIMEOUT_SECONDS


# --------------------------------------------------------------------------- API rules


@pytest.mark.db
async def test_validation_and_limits(db_urls: DbUrls, world: World) -> None:
    application = await _app(db_urls, report_max_changes=1)
    try:
        async with client_for(application) as client:
            headers = auth(world.auditor)
            base = {"kind": "register", "company_id": str(world.a.id)}
            no_period = await client.post("/api/v1/reports", json=base, headers=headers)
            assert_problem(no_period, 422, "report.period_required")
            backwards = await client.post(
                "/api/v1/reports",
                json={
                    **base,
                    "period_from": PERIOD["period_to"],
                    "period_to": PERIOD["period_from"],
                },
                headers=headers,
            )
            assert_problem(backwards, 422, "report.invalid_period")
            too_large = await client.post(
                "/api/v1/reports", json={**base, **PERIOD}, headers=headers
            )
            assert_problem(too_large, 422, "report.too_large")
            assert too_large.json()["max_changes"] == 1
            card_all = await client.post(
                "/api/v1/reports", json={"kind": "change_card", "company_id": None}, headers=headers
            )
            assert_problem(card_all, 422, "report.invalid_kind")
            csv = await client.get(
                f"/api/v1/companies/{world.a.id}/changes/export.csv", headers=headers
            )
            assert_problem(csv, 422, "report.too_large")
    finally:
        await application.state.db.dispose()


@pytest.mark.db
async def test_numbering_is_consecutive_per_company(rw_engine: AsyncEngine, world: World) -> None:
    roles = {world.a.id: {Role.AUDITOR}}
    first = await make_report(rw_engine, [world.a], world.auditor, roles)
    second = await make_report(rw_engine, [world.a], world.auditor, roles)
    prefix, year, value = first.number.rsplit("-", 2)
    assert prefix == f"RAP-{world.a.prefix}"
    assert second.number == f"{prefix}-{year}-{int(value) + 1:04d}"


@pytest.mark.db
async def test_listing_shows_only_what_the_user_may_export(
    api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    roles_a = {world.a.id: {Role.AUDITOR}}
    register = await make_report(rw_engine, [world.a], world.auditor, roles_a)
    assert world.draft_a is not None
    card = await make_report(
        rw_engine,
        [world.a],
        world.editor,
        {world.a.id: {Role.EDITOR}},
        kind="change_card",
        change=world.draft_a,
    )

    async def ids(user: User, **params: Any) -> set[str]:
        response = await api.get("/api/v1/reports", params=params, headers=auth(user))
        assert response.status_code == 200, response.text
        return {i["id"] for i in response.json()["items"]}

    editor_sees = await ids(world.editor)
    assert str(card.id) in editor_sees
    assert str(register.id) not in editor_sees
    assert {str(card.id), str(register.id)} <= await ids(world.approver)
    assert await ids(world.auditor, kind="change_card") >= {str(card.id)}
    assert str(register.id) not in await ids(world.auditor, kind="change_card")
    assert {str(card.id), str(register.id)} <= await ids(world.admin)
    item = next(
        i
        for i in (await api.get("/api/v1/reports", headers=auth(world.editor))).json()["items"]
        if i["id"] == str(card.id)
    )
    assert item["change_number"] == world.draft_a.number
    assert item["generated_by"]["display_name"] == world.editor.display_name
    assert item["company"]["prefix"] == world.a.prefix
    # The editor may not open a register report of their own company: 403 (recorded).
    denied = await api.get(f"/api/v1/reports/{register.id}", headers=auth(world.editor))
    assert_problem(denied, 403, "auth.forbidden")


@pytest.mark.db
async def test_admin_without_role_exports_on_the_named_admin_path(
    api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    created = await api.post(
        "/api/v1/reports",
        json={"kind": "register", "company_id": str(world.b.id), **PERIOD},
        headers=auth(world.admin),
    )
    assert created.status_code == 201, created.text
    (entry,) = await export_entries(rw_engine, UUID(created.json()["id"]))
    assert entry.company_id == world.b.id
    assert entry.context["admin_path"] is True
    assert entry.actor_roles == ["app_admin"]
    downloaded = await api.get(created.json()["download_url"], headers=auth(world.admin))
    assert downloaded.status_code == 200
    entries = await export_entries(rw_engine, UUID(created.json()["id"]))
    assert [e.context["event"] for e in entries] == ["generated", "downloaded"]
    assert entries[1].context["admin_path"] is True
    assert entries[1].company_id == world.b.id
    # The multi-company report is for auditors: the admin without the role gets 403.
    aggregate = await api.post(
        "/api/v1/reports",
        json={"kind": "register", "company_id": None, **PERIOD},
        headers=auth(world.admin),
    )
    assert_problem(aggregate, 403, "auth.forbidden")


@pytest.mark.db
async def test_tampered_or_missing_file_is_never_served(
    api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    report = await make_report(rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}})
    assert report.storage_key is not None
    path = Path(TEST_STORAGE) / report.storage_key
    tampered = path.read_bytes() + b"x"
    path.write_bytes(tampered)
    response = await api.get(f"/api/v1/reports/{report.id}/download", headers=auth(world.auditor))
    assert_problem(response, 500, "report.file_corrupted")
    path.unlink()
    response = await api.get(f"/api/v1/reports/{report.id}/download", headers=auth(world.auditor))
    assert_problem(response, 500, "report.file_missing")
    entries = await export_entries(rw_engine, report.id)
    # Nothing served, nothing recorded as downloaded - but each refusal is evidence,
    # recorded in a separate transaction (the request itself rolled back).
    assert [e.context["event"] for e in entries] == [
        "generated",
        "integrity_failed",
        "integrity_failed",
    ]
    corrupted, missing = entries[1], entries[2]
    for entry in (corrupted, missing):
        assert entry.company_id == world.a.id
        assert entry.entity_type == "report"
        assert entry.action == "export"
        assert entry.actor_id == world.auditor.id
        assert entry.context["number"] == report.number
        assert entry.context["expected_sha256"] == report.file_sha256
    assert corrupted.context["code"] == "report.file_corrupted"
    assert corrupted.context["found_sha256"] == hashlib.sha256(tampered).hexdigest()
    assert missing.context["code"] == "report.file_missing"
    assert missing.context["found_sha256"] is None
    assert (await verify(rw_engine, world.a.id)).ok


# --------------------------------------------------------------------------- database


@pytest.mark.db
async def test_finished_report_row_is_frozen_and_never_deleted(
    rw_engine: AsyncEngine, world: World
) -> None:
    report = await make_report(rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}})
    for statement in (
        "UPDATE report_exports SET status = 'failed', error = 'x' WHERE id = :id",
        "UPDATE report_exports SET data_sha256 = repeat('a', 64) WHERE id = :id",
        "UPDATE report_exports SET number = 'RAP-2026-9999' WHERE id = :id",
        "DELETE FROM report_exports WHERE id = :id",
    ):
        with pytest.raises(DBAPIError):
            async with scoped(rw_engine, [world.a.id]) as session:
                await session.execute(text(statement), {"id": report.id})


@pytest.mark.db
async def test_multi_company_rows_are_visible_to_their_author_and_the_admin_path_only(
    rw_engine: AsyncEngine, world: World
) -> None:
    other = await make_user(rw_engine)
    await grant(rw_engine, world.a, other, Role.AUDITOR)
    report = await make_report(
        rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}}, aggregate=True
    )
    assert report.company_id is None

    async def visible(user_id: UUID | None, *, admin: bool = False) -> bool:
        async with scoped(rw_engine, [world.a.id], admin_scope=admin) as session:
            if user_id is not None:
                await set_current_user(session, user_id)
            found = await session.execute(
                text("SELECT count(*) FROM report_exports WHERE id = :id"), {"id": report.id}
            )
            return bool(found.scalar_one())

    assert await visible(world.auditor.id)
    assert not await visible(other.id)  # another auditor of the same company
    assert not await visible(None)
    assert await visible(None, admin=True)

    # Writing a multi-company row needs every company of the report in the scope.
    async def insert_without_the_company_in_scope() -> None:
        async with scoped(rw_engine, []) as session:
            await set_current_user(session, world.auditor.id)
            await session.execute(
                text(
                    "INSERT INTO report_exports (number, kind, format, scope_company_ids, "
                    "generated_by_id) VALUES ('RAP-2026-99999', 'register', 'pdf', "
                    "ARRAY[CAST(:c AS uuid)], :u)"
                ),
                {"c": world.a.id, "u": world.auditor.id},
            )

    with pytest.raises(DBAPIError) as info:
        await insert_without_the_company_in_scope()
    assert "row-level security" in str(info.value)


@pytest.mark.db
async def test_report_kind_values_match_the_domain(rw_engine: AsyncEngine) -> None:
    assert {k.value for k in ReportKind} == {"register", "change_card"}
    async with scoped(rw_engine) as session:
        now = await db_now(session)
    assert now.tzinfo is not None


# --------------------------------------------------------------------------- review fixes


async def report_audit(engine: AsyncEngine, company_id: UUID) -> list[Any]:
    """Every ``report`` entry about ``company_id``: its chain and the global fallback."""
    async with scoped(engine, [company_id], global_read=True) as session:
        result = await session.execute(
            text(
                "SELECT * FROM audit_log WHERE entity_type = 'report' AND (company_id = :c "
                "OR (company_id IS NULL AND context->>'target_company_id' = :cs)) "
                "ORDER BY occurred_at, seq"
            ),
            {"c": company_id, "cs": str(company_id)},
        )
        return list(result.all())


async def report_rows(engine: AsyncEngine, company_id: UUID) -> list[ReportExport]:
    async with scoped(engine, [company_id]) as session:
        return list(
            (
                await session.execute(
                    select(ReportExport).where(ReportExport.company_id == company_id)
                )
            ).scalars()
        )


async def report_row(engine: AsyncEngine, company_ids: list[UUID], report_id: UUID) -> Any:
    async with scoped(engine, company_ids, admin_scope=True) as session:
        return (
            await session.execute(select(ReportExport).where(ReportExport.id == report_id))
        ).scalar_one()


async def order_in_background(
    small_app: FastAPI, small_api: AsyncClient, user: User, company: Company
) -> dict[str, Any]:
    body = {"kind": "register", "company_id": str(company.id), **PERIOD}
    created = await small_api.post("/api/v1/reports", json=body, headers=auth(user))
    assert created.status_code == 202, created.text
    job: dict[str, Any] = small_app.state.report_queue.jobs[-1]
    assert job["report_id"] == created.json()["id"]
    return job


async def run_job(engine: AsyncEngine, job: dict[str, Any], renderer: Any = stub_pdf) -> str:
    return await report_jobs.run(
        async_sessionmaker(engine, expire_on_commit=False),
        report_id=UUID(job["report_id"]),
        user_id=UUID(job["user_id"]),
        company_ids=[UUID(c) for c in job["company_ids"]],
        renderer=renderer,
        storage_root=TEST_STORAGE,
        max_changes=5000,
        admin_path=bool(job.get("admin_path", False)),
    )


def _failing_renderer(_: str) -> bytes:
    raise RuntimeError("renderer exploded")


@pytest.mark.db
async def test_worker_renderer_error_fails_the_report_without_a_file(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    job = await order_in_background(small_app, small_api, world.auditor, world.a)
    assert await run_job(rw_engine, job, _failing_renderer) == "failed"
    row = await report_row(rw_engine, [world.a.id], UUID(job["report_id"]))
    assert row.status == "failed"
    assert row.error == report_jobs.GENERIC_ERROR
    assert row.storage_key is None
    assert not (Path(TEST_STORAGE) / "reports" / str(world.a.id) / f"{row.id}.pdf").exists()
    entries = await export_entries(rw_engine, row.id)
    assert [e.context["event"] for e in entries] == ["requested", "failed"]
    assert entries[1].context["source"] == "worker"


@pytest.mark.db
async def test_worker_fails_the_report_of_an_inactive_user(
    small_app: FastAPI,
    small_api: AsyncClient,
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    world: World,
) -> None:
    orderer = await make_user(rw_engine)
    await grant(rw_engine, world.a, orderer, Role.AUDITOR)
    job = await order_in_background(small_app, small_api, orderer, world.a)
    await owner_exec(owner_engine, "UPDATE users SET is_active = false WHERE id = :u", u=orderer.id)
    assert await run_job(rw_engine, job) == "failed"
    row = await report_row(rw_engine, [world.a.id], UUID(job["report_id"]))
    assert (row.status, row.error, row.storage_key) == ("failed", report_jobs.NO_PERMISSION, None)
    events = [e.context["event"] for e in await export_entries(rw_engine, row.id)]
    assert events == ["requested", "failed"]


@pytest.mark.db
async def test_redis_unavailable_leaves_no_row_and_no_audit_entry(
    db_urls: DbUrls, world: World, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arq

    from app.reports.queue import ArqReportQueue

    async def unreachable(*_: Any, **__: Any) -> Any:
        raise ConnectionRefusedError("redis is down")

    monkeypatch.setattr(arq, "create_pool", unreachable)
    application = await _app(db_urls, report_async_threshold=1)
    application.state.report_queue = ArqReportQueue("redis://127.0.0.1:1/0")
    try:
        async with client_for(application) as client:
            response = await client.post(
                "/api/v1/reports",
                json={"kind": "register", "company_id": str(world.a.id), **PERIOD},
                headers=auth(world.auditor),
            )
    finally:
        await application.state.db.dispose()
    assert_problem(response, 503, "report.queue_unavailable")
    assert await report_rows(rw_engine, world.a.id) == []
    assert await report_audit(rw_engine, world.a.id) == []


@pytest.mark.db
async def test_cancelled_job_is_failed_in_a_new_transaction(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    """``job_timeout`` cancels the job: ``CancelledError`` bypasses ``except Exception`` -
    the row is failed in a NEW transaction before the cancellation propagates."""
    job = await order_in_background(small_app, small_api, world.auditor, world.a)

    def slow(html: str) -> bytes:
        time.sleep(1.5)
        return stub_pdf(html)

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(run_job(rw_engine, job, slow), timeout=0.3)
    row = await report_row(rw_engine, [world.a.id], UUID(job["report_id"]))
    assert (row.status, row.error, row.storage_key) == ("failed", report_jobs.TIMEOUT_ERROR, None)
    entries = await export_entries(rw_engine, row.id)
    assert [e.context["event"] for e in entries] == ["requested", "failed"]
    assert entries[1].context["source"] == "worker"
    # The job is not repeated into a second outcome.
    assert await run_job(rw_engine, job) == "skipped"


@pytest.mark.db
async def test_error_outside_the_generation_savepoint_fails_the_report(
    small_app: FastAPI,
    small_api: AsyncClient,
    rw_engine: AsyncEngine,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = await order_in_background(small_app, small_api, world.auditor, world.a)

    def broken(*_: Any) -> bool:
        raise RuntimeError("lost connection")

    monkeypatch.setattr(report_jobs, "still_allowed", broken)
    with pytest.raises(RuntimeError):
        await run_job(rw_engine, job)
    row = await report_row(rw_engine, [world.a.id], UUID(job["report_id"]))
    assert (row.status, row.error) == ("failed", report_jobs.GENERIC_ERROR)
    events = [e.context["event"] for e in await export_entries(rw_engine, row.id)]
    assert events == ["requested", "failed"]


@pytest.mark.db
async def test_maintenance_fails_stale_pending_reports_and_removes_orphans(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    from datetime import timedelta

    maker = async_sessionmaker(rw_engine, expire_on_commit=False)
    job = await order_in_background(small_app, small_api, world.auditor, world.a)
    report_id = UUID(job["report_id"])
    # Not stale yet: left alone.
    assert not await report_jobs.fail_pending(
        maker,
        report_id=report_id,
        user_id=world.auditor.id,
        company_ids=[world.a.id],
        error=report_jobs.TIMEOUT_ERROR,
        extra={"source": "maintenance"},
        stale_before=timedelta(hours=1),
    )
    assert (await report_row(rw_engine, [world.a.id], report_id)).status == "pending"
    # The job was lost: the maintenance fails it (as the ordering user, audited).
    assert await report_jobs.fail_stale(maker, stale_after=timedelta(0)) >= 1
    row = await report_row(rw_engine, [world.a.id], report_id)
    assert (row.status, row.error) == ("failed", report_jobs.TIMEOUT_ERROR)
    entries = await export_entries(rw_engine, report_id)
    assert [e.context["event"] for e in entries] == ["requested", "failed"]
    assert entries[1].context["source"] == "maintenance"
    assert entries[1].actor_id == world.auditor.id
    assert entries[1].company_id == world.a.id
    # A late job finds nothing to do.
    assert await run_job(rw_engine, job) == "skipped"

    # Orphaned files: no ``done`` row -> removed once old enough; stored reports stay.
    kept = await make_report(rw_engine, [world.a], world.auditor, {world.a.id: {Role.AUDITOR}})
    assert kept.storage_key is not None
    kept_path = Path(TEST_STORAGE) / kept.storage_key
    orphan = Path(TEST_STORAGE) / "reports" / str(world.a.id) / f"{uuid4()}.pdf"
    partial = Path(TEST_STORAGE) / "reports" / str(world.a.id) / f"{uuid4()}.pdf.part"
    fresh = Path(TEST_STORAGE) / "reports" / str(world.a.id) / f"{uuid4()}.csv"
    for path in (orphan, partial, fresh):
        path.write_bytes(b"x")
    old = time.time() - 7200
    for path in (orphan, partial, kept_path):
        os.utime(path, (old, old))
    removed = await report_jobs.remove_orphan_files(
        maker, storage_root=TEST_STORAGE, older_than=timedelta(hours=1)
    )
    assert removed >= 2
    assert not orphan.exists()
    assert not partial.exists()
    assert kept_path.exists()
    assert fresh.exists()  # may still be committed by a generation in progress
    fresh.unlink()


@pytest.mark.db
async def test_synchronous_failure_is_recorded_in_a_separate_transaction(
    db_urls: DbUrls, world: World, rw_engine: AsyncEngine
) -> None:
    application = await _app(db_urls)
    application.state.pdf_renderer = _failing_renderer
    assert world.implemented_a is not None
    try:
        async with client_for(application) as client:
            response = await client.post(
                "/api/v1/reports",
                json={
                    "kind": "change_card",
                    "company_id": str(world.a.id),
                    "change_id": str(world.implemented_a.id),
                },
                headers=auth(world.auditor),
            )
    finally:
        await application.state.db.dispose()
    assert response.status_code == 500
    assert await report_rows(rw_engine, world.a.id) == []  # rolled back with the request
    (entry,) = await report_audit(rw_engine, world.a.id)
    assert entry.company_id == world.a.id
    assert entry.action == "export"
    assert entry.actor_id == world.auditor.id
    assert entry.context["event"] == "failed"
    assert entry.context["persisted"] is False
    assert entry.context["exception"] == "RuntimeError"
    assert entry.context["error"] == reports_service.GENERIC_ERROR
    assert entry.context["change_id"] == str(world.implemented_a.id)
    assert "number" not in entry.context  # the number was rolled back with the row
    assert (await verify(rw_engine, world.a.id)).ok


@pytest.mark.db
async def test_multi_company_report_end_to_end(
    db_urls: DbUrls, rw_engine: AsyncEngine, world: World
) -> None:
    """An auditor in A and B (approver in C): the report holds A and B only, is numbered
    ``RAP-YYYY-NNNN``, recorded in the chains of A and B (never in the global one or in C)
    and cannot be downloaded once the role in B is gone."""
    c = await make_company(rw_engine)
    editor_c = await make_user(rw_engine)
    await grant(rw_engine, c, editor_c, Role.EDITOR)
    ci_c = await make_ci(rw_engine, c, world.ci_type, name="Serwer C")
    change_c = await make_change(
        rw_engine, c, editor_c, Role.EDITOR, values={"title": "Zmiana C", "ci_ids": [ci_c.id]}
    )
    auditor = await make_user(rw_engine, name="Audytor Grupy")
    await grant(rw_engine, world.a, auditor, Role.AUDITOR)
    await grant(rw_engine, world.b, auditor, Role.AUDITOR)
    await grant(rw_engine, c, auditor, Role.APPROVER)
    assert world.draft_a is not None
    assert world.draft_b is not None

    capture = Capture()
    application = await _app(db_urls)
    application.state.pdf_renderer = capture
    try:
        async with client_for(application) as client:
            created = await client.post(
                "/api/v1/reports",
                json={"kind": "register", "company_id": None, **PERIOD},
                headers=auth(auditor),
            )
            assert created.status_code == 201, created.text
            report = created.json()
            downloaded = await client.get(report["download_url"], headers=auth(auditor))
            assert downloaded.status_code == 200, downloaded.text
            await grant(rw_engine, world.b, auditor)  # the role in B is revoked
            denied = await client.get(report["download_url"], headers=auth(auditor))
            assert_problem(denied, 403, "auth.forbidden")
    finally:
        await application.state.db.dispose()

    assert re.fullmatch(r"RAP-\d{4}-\d{4,}", report["number"])
    assert report["company_id"] is None
    assert {x["prefix"] for x in report["companies"]} == {world.a.prefix, world.b.prefix}
    (html,) = capture.html
    assert world.draft_a.number in html
    assert world.draft_b.number in html
    assert change_c.number not in html
    assert c.name not in html

    entries = await export_entries(rw_engine, UUID(report["id"]))
    assert sorted((str(e.company_id), e.context["event"]) for e in entries) == sorted(
        (str(cid), event)
        for cid in (world.a.id, world.b.id)
        for event in ("generated", "downloaded")
    )
    assert all(e.company_id is not None for e in entries)  # nothing in the global chain
    assert all(e.company_id != c.id for e in entries)
    assert {e.context["number"] for e in entries} == {report["number"]}
    assert await report_audit(rw_engine, c.id) == []


@pytest.mark.db
async def test_admin_path_is_recorded_by_the_worker(
    small_app: FastAPI, small_api: AsyncClient, rw_engine: AsyncEngine, world: World
) -> None:
    await make_change(  # B needs more changes than the threshold (1)
        rw_engine,
        world.b,
        world.outsider,
        Role.EDITOR,
        values={"title": "Szkic B2", "ci_ids": [world.ci_b.id]},
    )
    job = await order_in_background(small_app, small_api, world.admin, world.b)
    assert job["admin_path"] is True
    assert await run_job(rw_engine, job) == "done"
    entries = await export_entries(rw_engine, UUID(job["report_id"]))
    assert [e.context["event"] for e in entries] == ["requested", "generated"]
    assert all(e.context["admin_path"] is True for e in entries)
    assert all(e.company_id == world.b.id for e in entries)
    assert entries[1].context["source"] == "worker"


@pytest.mark.db
async def test_broken_company_chain_falls_back_to_the_global_chain(
    api: AsyncClient, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    """A company chain that refuses the append (forged head) never blocks an export nor
    leaves it unrecorded: the entry goes to the global chain with ``target_company_id``
    (CSV, download and a refused download alike)."""
    company, auditor, _ = await _polish_world(rw_engine)
    await tamper_last_hash(owner_engine, company.id)

    csv = await api.get(f"/api/v1/companies/{company.id}/changes/export.csv", headers=auth(auditor))
    assert csv.status_code == 200, csv.text
    report_id = UUID(csv.headers["x-report-id"])
    downloaded = await api.get(f"/api/v1/reports/{report_id}/download", headers=auth(auditor))
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.content == csv.content

    async with scoped(rw_engine, [company.id]) as session:
        row = (
            await session.execute(select(ReportExport).where(ReportExport.id == report_id))
        ).scalar_one()
    assert row.storage_key is not None
    (Path(TEST_STORAGE) / row.storage_key).unlink()
    missing = await api.get(f"/api/v1/reports/{report_id}/download", headers=auth(auditor))
    assert_problem(missing, 500, "report.file_missing")

    entries = await export_entries(rw_engine, report_id)
    assert [e.context["event"] for e in entries] == [
        "generated",
        "downloaded",
        "integrity_failed",
    ]
    for entry in entries:
        assert entry.company_id is None
        assert entry.context["target_company_id"] == str(company.id)
        assert entry.context["chain_append_failed"] is True
    assert (await verify(rw_engine, None)).ok


@pytest.mark.db
async def test_admin_export_path_scope_is_the_target_company_only(
    api: AsyncClient,
    rw_engine: AsyncEngine,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin without a role: scope = the target company only, no admin_scope, no global
    audit read, writable. Admin WITH a role there: the member path (ADR 0016)."""
    seen: list[dict[str, Any]] = []

    async def settings_of(session: Any) -> dict[str, Any]:
        row = (
            await session.execute(
                text(
                    "SELECT current_setting('app.company_ids', true) AS ids, "
                    "current_setting('app.audit_global_read', true) AS global_read, "
                    "current_setting('app.admin_scope', true) AS admin_scope, "
                    "current_setting('transaction_read_only') AS read_only"
                )
            )
        ).one()
        return dict(row._mapping)

    original_csv = reports_service.export_csv
    original_create = reports_service.create_report
    original_download = reports_service.download

    async def csv_spy(session: Any, **kwargs: Any) -> Any:
        current = await settings_of(session)
        seen.append({"route": "csv", "admin_path": kwargs["admin_path"], **current})
        return await original_csv(session, **kwargs)

    async def create_spy(session: Any, **kwargs: Any) -> Any:
        seen.append({"route": "create", **await settings_of(session)})
        return await original_create(session, **kwargs)

    async def download_spy(session: Any, report: Any, **kwargs: Any) -> Any:
        seen.append({"route": "download", **await settings_of(session)})
        return await original_download(session, report, **kwargs)

    monkeypatch.setattr(reports_service, "export_csv", csv_spy)
    monkeypatch.setattr(reports_service, "create_report", create_spy)
    monkeypatch.setattr(reports_service, "download", download_spy)

    target = "{" + str(world.b.id) + "}"
    admin = auth(world.admin)
    csv = await api.get(f"/api/v1/companies/{world.b.id}/changes/export.csv", headers=admin)
    assert csv.status_code == 200, csv.text
    created = await api.post(
        "/api/v1/reports",
        json={"kind": "register", "company_id": str(world.b.id), **PERIOD},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    downloaded = await api.get(created.json()["download_url"], headers=admin)
    assert downloaded.status_code == 200, downloaded.text
    for item in seen:
        assert item["ids"] == target, item
        assert item["global_read"] == "off", item
        assert item["admin_scope"] == "off", item
        assert item["read_only"] == "off", item
    assert seen[0]["admin_path"] is True
    (csv_entry,) = await export_entries(rw_engine, UUID(csv.headers["x-report-id"]))
    assert csv_entry.context["admin_path"] is True

    # The admin with a role in A exports A as a member: no admin path.
    seen.clear()
    await grant(rw_engine, world.a, world.admin, Role.AUDITOR)
    member = await api.get(f"/api/v1/companies/{world.a.id}/changes/export.csv", headers=admin)
    assert member.status_code == 200, member.text
    assert seen[0]["admin_path"] is False
    assert seen[0]["admin_scope"] == "off"
    (member_entry,) = await export_entries(rw_engine, UUID(member.headers["x-report-id"]))
    assert "admin_path" not in member_entry.context
    assert set(member_entry.actor_roles) == {"app_admin", "auditor"}


@pytest.mark.db
async def test_appendix_b_says_when_a_trail_is_truncated_and_the_card_never_is(
    rw_engine: AsyncEngine, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reports_service, "TRAIL_LIMIT_PER_CHANGE", 2)
    assert world.implemented_a is not None
    capture = Capture()
    report = await make_report(
        rw_engine,
        [world.a],
        world.auditor,
        {world.a.id: {Role.AUDITOR}},
        include_audit_trail=True,
        renderer=capture,
    )
    async with scoped(rw_engine, [world.a.id]) as session:
        await set_current_user(session, world.auditor.id)
        data = await reports_service.build_data(
            session,
            report=report,
            generated_by=world.auditor.display_name,
            now=await db_now(session),
            max_changes=5000,
        )
    trails = {t["number"]: t for t in data["audit_trails"]}
    implemented = trails[world.implemented_a.number]
    assert len(implemented["entries"]) == 2
    assert implemented["truncated"] is True
    assert implemented["omitted"] >= 2  # create, submit, approve, implement
    assert data["audit_trail_limit"] == 2
    assert data["audit_trails_truncated"] == sum(1 for t in trails.values() if t["truncated"])
    html = capture.html[0]
    assert "Ścieżka skrócona" in html
    assert "została skrócona do 2 pierwszych wpisów" in html

    card = await make_report(
        rw_engine,
        [world.a],
        world.auditor,
        {world.a.id: {Role.AUDITOR}},
        kind="change_card",
        change=world.implemented_a,
    )
    async with scoped(rw_engine, [world.a.id]) as session:
        await set_current_user(session, world.auditor.id)
        card_data = await reports_service.build_data(
            session,
            report=card,
            generated_by=world.auditor.display_name,
            now=await db_now(session),
            max_changes=5000,
        )
    assert len(card_data["audit_trail"]) == 2 + implemented["omitted"]
