"""Change tables at the database level (migration 0008, ADR 0013) and attachments.

Runs as ``app_rw`` with explicit scopes WITHOUT the services where possible: it proves
what the database alone enforces (append-only comments / attachments / consents, status
only through the action path, freezing, version steps, numbering steps, RLS, grants).
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db import apply_company_scope
from app.main import create_app
from app.permissions import Role
from app.services import attachments as attachments_service
from tests.conftest import TEST_STORAGE, DbUrls, make_settings
from tests.factories import (
    World,
    act,
    add_changes,
    audit_entries,
    auth,
    client_for,
    make_change,
    ready_values,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
INSUFFICIENT_PRIVILEGE = "42501"
RESTRICT_VIOLATION = "23001"
CHECK_VIOLATION = "23514"
FOREIGN_KEY_VIOLATION = "23503"


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@asynccontextmanager
async def tx(engine: AsyncEngine, company_ids: Sequence[UUID]) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as session:
        await session.begin()
        await apply_company_scope(session, company_ids)
        try:
            yield session
        finally:
            await session.rollback()


async def fails(
    engine: AsyncEngine, company_ids: Sequence[UUID], *statements: tuple[str, dict[str, Any]]
) -> str | None:
    try:
        async with tx(engine, company_ids) as session:
            for sql, params in statements:
                await session.execute(text(sql), params)
    except DBAPIError as exc:
        return sqlstate(exc)
    return None


ACTION_PATH = ("SELECT set_config('app.change_action', CAST(:id AS text), true)", {})


def action_path(change_id: UUID) -> tuple[str, dict[str, Any]]:
    return (ACTION_PATH[0], {"id": str(change_id)})


@pytest.fixture
async def cworld(world: World, rw_engine: AsyncEngine) -> World:
    return await add_changes(rw_engine, world)


# --------------------------------------------------------------------------- grants, RLS


async def test_app_rw_privileges_on_change_tables(rw_engine: AsyncEngine) -> None:
    expected = {
        "changes": {"SELECT", "INSERT", "UPDATE"},
        "change_items": {"SELECT", "INSERT", "UPDATE", "DELETE"},
        "number_sequences": {"SELECT", "INSERT", "UPDATE"},
        "change_comments": {"SELECT", "INSERT"},
        "attachments": {"SELECT", "INSERT"},
        "change_ci_consents": {"SELECT", "INSERT"},
    }
    async with rw_engine.connect() as conn:
        for table, privileges in expected.items():
            granted = {
                p
                for p in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
                if (
                    await conn.execute(
                        text("SELECT has_table_privilege('app_rw', :t, :p)"),
                        {"t": f"public.{table}", "p": p},
                    )
                ).scalar_one()
            }
            assert granted == privileges, table


async def test_change_rows_are_isolated_by_rls(rw_engine: AsyncEngine, cworld: World) -> None:
    w = cworld
    tables = ("changes", "change_items", "change_comments", "attachments", "number_sequences")
    async with tx(rw_engine, [w.a.id]) as session:
        seen = {
            t: set(
                (await session.execute(text(f"SELECT DISTINCT company_id FROM {t}"))).scalars()  # noqa: S608
            )
            for t in tables
        }
        foreign = (
            await session.execute(
                text("SELECT count(*) FROM changes WHERE id = :id"),
                {"id": w.draft_b.id},  # type: ignore[union-attr]
            )
        ).scalar_one()
    assert all(companies <= {w.a.id} for companies in seen.values()), seen
    assert seen["changes"] == {w.a.id}
    assert foreign == 0
    # Writing a row of another company is refused by WITH CHECK.
    insert = (
        "INSERT INTO change_comments (company_id, change_id, author_id, body) "
        "VALUES (:c, :ch, :u, 'x')",
        {"c": w.b.id, "ch": w.draft_b.id, "u": w.editor.id},  # type: ignore[union-attr]
    )
    assert await fails(rw_engine, [w.a.id], insert) == INSUFFICIENT_PRIVILEGE


async def test_child_rows_cannot_point_to_another_company(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    """Composite FK (change_id, company_id): a row of A cannot hang on B's change."""
    w = cworld
    cross = (
        "INSERT INTO change_items (company_id, change_id, ci_id) VALUES (:c, :ch, :ci)",
        {"c": w.a.id, "ch": w.draft_b.id, "ci": w.ci_a.id},  # type: ignore[union-attr]
    )
    assert await fails(rw_engine, [w.a.id, w.b.id], cross) == FOREIGN_KEY_VIOLATION
    foreign_ci = (
        "INSERT INTO change_items (company_id, change_id, ci_id) VALUES (:c, :ch, :ci)",
        {"c": w.a.id, "ch": w.draft_a.id, "ci": w.ci_b.id},  # type: ignore[union-attr]
    )
    assert await fails(rw_engine, [w.a.id, w.b.id], foreign_ci) == FOREIGN_KEY_VIOLATION


# --------------------------------------------------------------------------- append-only


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE change_comments SET body = 'zmieniony' WHERE change_id = :ch",
        "DELETE FROM change_comments WHERE change_id = :ch",
        "UPDATE attachments SET sha256 = repeat('0', 64) WHERE change_id = :ch",
        "DELETE FROM attachments WHERE change_id = :ch",
        "DELETE FROM changes WHERE id = :ch",
        "TRUNCATE change_comments",
    ],
)
async def test_comments_and_attachments_cannot_be_changed_by_app_rw(
    rw_engine: AsyncEngine, cworld: World, sql: str
) -> None:
    w = cworld
    params = {"ch": w.draft_a.id}  # type: ignore[union-attr]
    assert await fails(rw_engine, [w.a.id], (sql, params)) == INSUFFICIENT_PRIVILEGE


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE change_comments SET body = 'zmieniony'",
        "DELETE FROM change_comments",
        "UPDATE attachments SET filename = 'inny.txt'",
        "DELETE FROM attachments",
        "TRUNCATE change_ci_consents",
        "TRUNCATE attachments",
    ],
)
async def test_even_the_owner_cannot_change_appended_rows(
    owner_engine: AsyncEngine, cworld: World, sql: str
) -> None:
    async with owner_engine.connect() as conn:
        await conn.execute(
            text(
                "INSERT INTO change_comments (company_id, change_id, author_id, body) "
                "VALUES (:c, :ch, :u, 'komentarz')"
            ),
            {"c": cworld.a.id, "ch": cworld.draft_a.id, "u": cworld.editor.id},  # type: ignore[union-attr]
        )
        with pytest.raises(DBAPIError) as info:
            await conn.execute(text(sql))
        await conn.rollback()
    assert sqlstate(info.value) == RESTRICT_VIOLATION


# --------------------------------------------------------------------------- changes guard


async def test_status_changes_only_on_the_action_path(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    w = cworld
    ch = w.draft_a.id  # type: ignore[union-attr]
    direct = (
        "UPDATE changes SET status = 'cancelled', version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    assert await fails(rw_engine, [w.a.id], direct) == RESTRICT_VIOLATION
    # On the action path of ANOTHER change it is refused too.
    assert await fails(rw_engine, [w.a.id], action_path(uuid4()), direct) == RESTRICT_VIOLATION
    assert await fails(rw_engine, [w.a.id], action_path(ch), direct) is None
    # The action path never edits the business fields.
    both = (
        "UPDATE changes SET title = 'x', version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    assert await fails(rw_engine, [w.a.id], action_path(ch), both) == RESTRICT_VIOLATION
    # Timestamps belong to the action path as well.
    stamp = (
        "UPDATE changes SET approved_at = now(), version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    assert await fails(rw_engine, [w.a.id], stamp) == RESTRICT_VIOLATION


@pytest.mark.parametrize(
    ("sql", "state"),
    [
        ("UPDATE changes SET title = 'x' WHERE id = :ch", CHECK_VIOLATION),  # no version step
        ("UPDATE changes SET title = 'x', version = version + 2 WHERE id = :ch", CHECK_VIOLATION),
        ("UPDATE changes SET number = 'CHG-XX-2026-0001', version = version + 1 WHERE id = :ch",
         RESTRICT_VIOLATION),
        ("UPDATE changes SET requested_by_id = approver_id, version = version + 1 WHERE id = :ch",
         RESTRICT_VIOLATION),
        ("UPDATE changes SET window_end = window_start - interval '1 hour', "
         "version = version + 1 WHERE id = :ch", CHECK_VIOLATION),
    ],
)  # fmt: skip
async def test_change_identity_and_version_rules(
    rw_engine: AsyncEngine, cworld: World, sql: str, state: str
) -> None:
    w = cworld
    assert await fails(rw_engine, [w.a.id], (sql, {"ch": w.draft_a.id})) == state  # type: ignore[union-attr]


async def test_implemented_change_is_frozen_in_the_database(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    w = cworld
    pending = w.pending_a
    assert pending is not None
    approved = await act(rw_engine, w.a, pending, w.approver, "approve", Role.APPROVER)
    implemented = await act(rw_engine, w.a, approved, w.editor, "implement", Role.EDITOR)
    ch = implemented.id
    edit = (
        "UPDATE changes SET title = 'Po wdrożeniu', version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    assert await fails(rw_engine, [w.a.id], edit) == RESTRICT_VIOLATION
    add_ci = (
        "INSERT INTO change_items (company_id, change_id, ci_id) "
        "SELECT company_id, :ch, id FROM configuration_items WHERE id = :ci",
        {"ch": ch, "ci": uuid4()},
    )
    # nothing selected -> nothing inserted; use a real CI of A
    add_real = (
        "INSERT INTO change_items (company_id, change_id, ci_id) VALUES (:c, :ch, :ci)",
        {"c": w.a.id, "ch": ch, "ci": (await _other_ci(rw_engine, w))},
    )
    assert await fails(rw_engine, [w.a.id], add_ci) is None
    assert await fails(rw_engine, [w.a.id], add_real) == RESTRICT_VIOLATION
    remove = ("DELETE FROM change_items WHERE change_id = :ch", {"ch": ch})
    assert await fails(rw_engine, [w.a.id], remove) == RESTRICT_VIOLATION
    snapshot = ("UPDATE change_items SET ci_name = 'inna' WHERE change_id = :ch", {"ch": ch})
    assert await fails(rw_engine, [w.a.id], snapshot) == RESTRICT_VIOLATION
    assert await fails(rw_engine, [w.a.id], action_path(ch), snapshot) == RESTRICT_VIOLATION
    # The verifier may be re-pointed by the state machine (owner decision) - not frozen here.
    verifier = (
        "UPDATE changes SET verifier_id = :u, version = version + 1 WHERE id = :ch",
        {"ch": ch, "u": w.approver.id},
    )
    assert await fails(rw_engine, [w.a.id], verifier) is None


async def _other_ci(engine: AsyncEngine, world: World) -> UUID:
    from tests.factories import make_ci

    return (await make_ci(engine, world.a, world.ci_type)).id


async def test_four_eyes_and_completeness_checks(rw_engine: AsyncEngine, cworld: World) -> None:
    w = cworld
    ch = w.pending_a.id  # type: ignore[union-attr]
    self_approval = (
        "UPDATE changes SET status = 'approved', approved_at = now(), "
        "approved_by_id = requested_by_id, version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    make_self = (
        "UPDATE changes SET approver_id = requested_by_id, version = version + 1 WHERE id = :ch",
        {"ch": ch},
    )
    assert (
        await fails(rw_engine, [w.a.id], make_self, action_path(ch), self_approval)
        == CHECK_VIOLATION
    )
    incomplete = (
        "UPDATE changes SET status = 'pending_approval', version = version + 1 WHERE id = :ch",
        {"ch": w.draft_b.id},  # type: ignore[union-attr]
    )
    assert (
        await fails(rw_engine, [w.b.id], action_path(w.draft_b.id), incomplete)  # type: ignore[union-attr]
        == CHECK_VIOLATION
    )


async def test_number_sequences_step_by_one(rw_engine: AsyncEngine, cworld: World) -> None:
    w = cworld
    skip = (
        "UPDATE number_sequences SET last_value = last_value + 2 WHERE company_id = :c",
        {"c": w.a.id},
    )
    back = (
        "UPDATE number_sequences SET last_value = last_value - 1 WHERE company_id = :c",
        {"c": w.a.id},
    )
    start = (
        "INSERT INTO number_sequences (company_id, year, last_value) VALUES (:c, 2099, 5)",
        {"c": w.a.id},
    )
    for statement in (skip, back, start):
        assert await fails(rw_engine, [w.a.id], statement) == CHECK_VIOLATION


# --------------------------------------------------------------------------- attachments


async def test_attachment_upload_download_and_sha256(
    api: AsyncClient, cworld: World, rw_engine: AsyncEngine
) -> None:
    w = cworld
    url = f"/api/v1/companies/{w.a.id}/changes/{w.draft_a.id}/attachments"  # type: ignore[union-attr]
    # A PNG by its signature; the client's Content-Type is only recorded, not trusted.
    content = PNG_SIGNATURE + "zażółć gęślą jaźń\n".encode() * 100
    upload = await api.post(
        url,
        files={"file": ("../../etc/zrzut ekranu.png", content, "Image/PNG; charset=binary")},
        headers=auth(w.editor),
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["sha256"] == hashlib.sha256(content).hexdigest()
    assert body["size"] == len(content)
    assert body["filename"] == "zrzut ekranu.png"  # no path, only the name
    assert body["content_type"] == "image/png"
    assert upload.headers["Location"].endswith(body["id"])
    stored = attachments_service.resolve(
        TEST_STORAGE, attachments_service.storage_key(w.a.id, UUID(body["id"]))
    )
    assert stored.read_bytes() == content
    assert stored.is_relative_to(TEST_STORAGE.resolve())

    download = await api.get(f"{url}/{body['id']}", headers=auth(w.viewer))
    assert download.status_code == 200
    assert download.content == content
    assert download.headers["content-type"] == "image/png"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["x-content-sha256"] == body["sha256"]
    assert download.headers["content-disposition"].startswith("attachment;")

    # A new version is a new attachment; the list shows both, oldest first.
    again = await api.post(
        url, files={"file": ("zrzut ekranu.png", b"v2", "image/png")}, headers=auth(w.approver)
    )
    listed = await api.get(url, headers=auth(w.auditor))
    assert [a["id"] for a in listed.json()][-2:] == [body["id"], again.json()["id"]]

    entries = await audit_entries(rw_engine, UUID(body["id"]))
    assert [(e.entity_type, e.action) for e in entries] == [
        ("attachment", "attach"),
        ("attachment", "download"),
    ]
    assert entries[0].context["sha256"] == body["sha256"]
    assert entries[0].context["content_type"] == "image/png"
    assert entries[0].context["declared_content_type"] == "image/png"
    assert entries[0].context["change_id"] == str(w.draft_a.id)  # type: ignore[union-attr]
    assert (await verify(rw_engine, w.a.id)).ok

    assert_problem(
        await api.get(f"{url}/{uuid4()}", headers=auth(w.viewer)), 404, "attachment.not_found"
    )
    # HTML is refused whatever the client claims (415, ADR 0019 §3).
    html = await api.post(
        url,
        files={"file": ("x.txt", b"<script>alert(1)</script>", "text/plain")},
        headers=auth(w.editor),
    )
    assert_problem(html, 415, "attachment.type_not_allowed")
    empty = await api.post(
        url, files={"file": ("pusty.txt", b"", "text/plain")}, headers=auth(w.editor)
    )
    assert_problem(empty, 422, "attachment.empty")
    assert_problem(
        await api.post(url, files={"file": ("a.txt", b"a", "text/plain")}, headers=auth(w.viewer)),
        403,
        "auth.forbidden",
    )


async def test_attachment_size_limit(db_urls: DbUrls, cworld: World, tmp_path: Path) -> None:
    w = cworld
    app = create_app(
        make_settings(database_url=db_urls.rw, storage_path=tmp_path, attachment_max_bytes=10)
    )
    url = f"/api/v1/companies/{w.a.id}/changes/{w.draft_a.id}/attachments"  # type: ignore[union-attr]
    try:
        async with client_for(app) as client:
            ok = await client.post(
                url, files={"file": ("a.txt", b"0123456789", "text/plain")}, headers=auth(w.editor)
            )
            big = await client.post(
                url, files={"file": ("b.txt", b"01234567890", "text/plain")}, headers=auth(w.editor)
            )
    finally:
        await app.state.db.dispose()
    assert ok.status_code == 201
    assert_problem(big, 413, "attachment.too_large")
    # Only the accepted file is in the storage (the refused one was removed).
    assert len(_files(tmp_path)) == 1


async def test_attachment_type_whitelist(
    db_urls: DbUrls, cworld: World, tmp_path: Path, rw_engine: AsyncEngine
) -> None:
    """The stored type is detected from the content; types outside the whitelist get 415
    ``attachment.type_not_allowed`` and leave neither a file nor a row nor an audit entry."""
    w = cworld
    app = create_app(
        make_settings(
            database_url=db_urls.rw,
            storage_path=tmp_path,
            attachment_allowed_types="application/pdf,text/plain,text/csv",
        )
    )
    url = f"/api/v1/companies/{w.a.id}/changes/{w.draft_a.id}/attachments"  # type: ignore[union-attr]
    try:
        async with client_for(app) as client:
            pdf = await client.post(
                url,
                files={"file": ("raport.bin", b"%PDF-1.7\n...", "application/octet-stream")},
                headers=auth(w.editor),
            )
            csv = await client.post(
                url,
                files={"file": ("lista.csv", "a;b\nżółw;1\n".encode(), "text/plain")},
                headers=auth(w.editor),
            )
            exe = await client.post(
                url,
                files={
                    "file": ("instrukcja.pdf", b"MZ\x90\x00\x03\x00\x00\x00", "application/pdf")
                },
                headers=auth(w.editor),
            )
            png = await client.post(
                url,
                files={"file": ("ekran.png", PNG_SIGNATURE + b"\x00\x00", "image/png")},
                headers=auth(w.editor),
            )
            listed = await client.get(url, headers=auth(w.viewer))
    finally:
        await app.state.db.dispose()
    assert pdf.status_code == 201, pdf.text
    assert pdf.json()["content_type"] == "application/pdf"
    assert csv.status_code == 201, csv.text
    assert csv.json()["content_type"] == "text/csv"
    body = assert_problem(exe, 415, "attachment.type_not_allowed")
    assert body["detected_type"] == "application/x-msdownload"
    assert body["allowed_types"] == ["application/pdf", "text/csv", "text/plain"]
    assert "Niedozwolony typ pliku" in body["detail"]
    # PNG is a known type, but not on this whitelist.
    assert assert_problem(png, 415, "attachment.type_not_allowed")["detected_type"] == "image/png"
    names = {a["filename"] for a in listed.json()}
    assert {"raport.bin", "lista.csv"} <= names
    assert not {"instrukcja.pdf", "ekran.png"} & names
    assert len(_files(tmp_path)) == 2  # refused uploads removed (no .part leftovers)


def _files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def test_filename_and_content_type_sanitizing() -> None:
    sanitize = attachments_service.sanitize_filename
    assert sanitize("C:\\Users\\x\\raport.pdf") == "raport.pdf"
    assert sanitize("../../etc/passwd") == "passwd"
    assert sanitize("..") == "plik"
    assert sanitize(None) == "plik"
    assert sanitize("a\x00b\u202ec.txt") == "abc.txt"
    long = sanitize("x" * 300 + ".pdf")
    assert len(long) == 255
    assert long.endswith(".pdf")
    assert len(sanitize("y" * 300)) == 255
    normalize = attachments_service.normalize_content_type
    assert normalize("TEXT/Plain; charset=utf-8") == "text/plain"
    assert normalize("nonsense") == "application/octet-stream"
    assert normalize(None) == "application/octet-stream"


async def test_ready_values_factory_creates_ready_drafts(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    """Sanity check of the factories used by the permission and isolation tests."""
    w = cworld
    change = await make_change(
        rw_engine,
        w.a,
        w.editor,
        Role.EDITOR,
        values=ready_values(
            category=w.category, ci=[w.ci_a], assignee=w.editor, approver=w.approver
        ),
    )
    submitted = await act(rw_engine, w.a, change, w.editor, "submit", Role.EDITOR)
    assert submitted.status == "pending_approval"


# --------------------------------------------------------------------------- review fixes


async def test_approved_change_fields_are_frozen(rw_engine: AsyncEngine, cworld: World) -> None:
    w = cworld
    assert w.approved_a is not None
    ch = w.approved_a.id
    for column, value in (
        ("title", "'Po zatwierdzeniu'"),
        ("verifier_id", "requested_by_id"),
        ("approver_id", "NULL"),
        ("window_end", "window_end + interval '1 hour'"),
    ):
        sql = f"UPDATE changes SET {column} = {value}, version = version + 1 WHERE id = :ch"  # noqa: S608
        assert await fails(rw_engine, [w.a.id], (sql, {"ch": ch})) == RESTRICT_VIOLATION, column
    add_ci = (
        "INSERT INTO change_items (company_id, change_id, ci_id) VALUES (:c, :ch, :ci)",
        {"c": w.a.id, "ch": ch, "ci": await _other_ci(rw_engine, w)},
    )
    assert await fails(rw_engine, [w.a.id], add_ci) == RESTRICT_VIOLATION


async def test_rejected_and_cancelled_changes_are_closed(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    w = cworld
    assert w.draft_a is not None
    cancelled = await act(rw_engine, w.a, w.draft_a, w.editor, "cancel", Role.EDITOR)
    bump = ("UPDATE changes SET version = version + 1 WHERE id = :ch", {"ch": cancelled.id})
    assert await fails(rw_engine, [w.a.id], bump) == RESTRICT_VIOLATION
    on_path = await fails(rw_engine, [w.a.id], action_path(cancelled.id), bump)
    assert on_path == RESTRICT_VIOLATION
    remove = ("DELETE FROM change_items WHERE change_id = :ch", {"ch": cancelled.id})
    assert await fails(rw_engine, [w.a.id], remove) == RESTRICT_VIOLATION


async def test_approver_of_record_is_set_only_by_an_action(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    w = cworld
    assert w.approved_a is not None
    assert w.pending_a is not None
    assert w.approved_a.approved_by_id == w.approver.id
    forge = (
        "UPDATE changes SET approved_by_id = NULL, version = version + 1 WHERE id = :ch",
        {"ch": w.approved_a.id},
    )
    assert await fails(rw_engine, [w.a.id], forge) == RESTRICT_VIOLATION
    # on the action path: only the designated approver, only with approved_at
    other = (
        "UPDATE changes SET status = 'approved', approved_at = now(), approved_by_id = :u, "
        "version = version + 1 WHERE id = :ch",
        {"ch": w.pending_a.id, "u": w.viewer.id},
    )
    assert await fails(rw_engine, [w.a.id], action_path(w.pending_a.id), other) == CHECK_VIOLATION


async def test_approver_of_an_implemented_change_is_frozen_except_emergency(
    rw_engine: AsyncEngine, cworld: World
) -> None:
    w = cworld
    assert w.implemented_a is not None
    repoint = (
        "UPDATE changes SET approver_id = :u, version = version + 1 WHERE id = :ch",
        {"ch": w.implemented_a.id, "u": w.viewer.id},
    )
    assert await fails(rw_engine, [w.a.id], repoint) == RESTRICT_VIOLATION
    emergency = await make_change(
        rw_engine,
        w.a,
        w.editor,
        Role.EDITOR,
        values=ready_values(
            category=w.category,
            ci=[w.ci_a],
            assignee=w.editor,
            approver=w.approver,
            change_type="emergency",
        ),
    )
    emergency = await act(rw_engine, w.a, emergency, w.editor, "implement", Role.EDITOR)
    allowed = (
        "UPDATE changes SET approver_id = :u, version = version + 1 WHERE id = :ch",
        {"ch": emergency.id, "u": w.viewer.id},
    )
    assert await fails(rw_engine, [w.a.id], allowed) is None
