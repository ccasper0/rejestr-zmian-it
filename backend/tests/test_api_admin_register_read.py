"""The app admin's narrow read-only path to the change register of a company without a
role in it (owner decision 2026-11-02, variant "a"; ADR 0016).

- reads (list, card by id / number, readiness, change audit trail, attachment list,
  tiles, chain status) work, the card has ``access = "admin_read_only"`` and no actions or
  editable fields;
- the transaction holds only that company and is READ ONLY;
- every write, action, comment, upload and the attachment DOWNLOAD stays 404 +
  ``access_denied`` (global chain);
- an admin WITH a role in the company is resolved by that role (unchanged);
- auditors and others without membership still get 404.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.principal import CompanyContext
from app.db import SessionDep
from app.permissions import Role, require_register_read
from app.services import changes as changes_service
from tests.factories import (
    World,
    add_changes,
    auth,
    change_actor,
    client_for,
    grant,
    make_user,
    scoped,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db


@pytest.fixture
async def world(world: World, rw_engine: AsyncEngine) -> World:
    return await add_changes(rw_engine, world)


def _company(w: World, company_id: UUID | None = None) -> str:
    return f"/api/v1/companies/{company_id or w.a.id}"


def _change(w: World, suffix: str = "") -> str:
    assert w.draft_a is not None
    return f"{_company(w)}/changes/{w.draft_a.id}{suffix}"


async def _company_chain_length(engine: AsyncEngine, company_id: UUID) -> int:
    async with scoped(engine, [company_id]) as session:
        count = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": company_id}
            )
        ).scalar_one()
    return int(count)


async def _denials(engine: AsyncEngine, response: Response) -> list[Any]:
    async with scoped(engine, global_read=True) as session:
        result = await session.execute(
            text(
                "SELECT * FROM audit_log WHERE company_id IS NULL "
                "AND action = 'access_denied' AND request_id = :r"
            ),
            {"r": response.headers["X-Request-ID"]},
        )
        return list(result.all())


# --------------------------------------------------------------------------- reads


async def test_admin_without_role_reads_the_register(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    assert world.draft_a is not None
    assert world.attachment_a is not None
    headers = auth(world.admin)
    chain_before = await _company_chain_length(rw_engine, world.a.id)

    listing = await api.get(f"{_company(world)}/changes", headers=headers)
    assert listing.status_code == 200, listing.text
    numbers = {item["number"] for item in listing.json()["items"]}
    assert listing.json()["total"] == 4  # draft, pending, approved, implemented of A
    assert world.draft_a.number in numbers
    assert all(item["company_id"] == str(world.a.id) for item in listing.json()["items"])
    filtered = await api.get(
        f"{_company(world)}/changes", params={"status": "draft"}, headers=headers
    )
    assert filtered.status_code == 200
    assert {i["status"] for i in filtered.json()["items"]} == {"draft"}

    for url in (_change(world), f"{_company(world)}/changes/by-number/{world.draft_a.number}"):
        card = await api.get(url, headers=headers)
        assert card.status_code == 200, card.text
        body = card.json()
        assert body["id"] == str(world.draft_a.id)
        assert body["access"] == "admin_read_only"
        assert body["allowed_actions"] == []
        assert body["editable_fields"] == []
        assert card.headers["ETag"] == f'"{body["version"]}"'

    readiness = await api.get(_change(world, "/readiness"), headers=headers)
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["checks"]

    trail = await api.get(_change(world, "/audit"), headers=headers)
    assert trail.status_code == 200, trail.text
    entries = trail.json()["items"]
    assert entries
    assert all(e["hash_valid"] for e in entries)
    assert {e["entity_type"] for e in entries} >= {"change", "attachment"}

    attachments = await api.get(_change(world, "/attachments"), headers=headers)
    assert attachments.status_code == 200, attachments.text
    (attachment,) = attachments.json()
    assert attachment["id"] == str(world.attachment_a.id)
    assert attachment["sha256"] == world.attachment_a.sha256

    stats = await api.get(f"{_company(world)}/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    assert stats.json()["pending_approval"] == 1

    status = await api.get(f"{_company(world)}/audit/status", headers=headers)
    assert status.status_code == 200, status.text

    # Reads add nothing to the company chain (no audit entry per view, ADR 0013 §11).
    assert await _company_chain_length(rw_engine, world.a.id) == chain_before
    assert (await verify(rw_engine, world.a.id)).ok


async def test_admin_read_path_sees_correction_links(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """ADR 0021 on the narrow read path (ADR 0016): both directions of a correction."""
    original = world.implemented_a
    assert original is not None
    async with scoped(rw_engine, [world.a.id]) as session:
        correction = await changes_service.create_change(
            session,
            actor=change_actor(world.editor, world.a, Role.EDITOR),
            company=world.a,
            values={"title": "Korekta wdrożonej zmiany"},
            supersedes_change_id=original.id,
        )
    headers = auth(world.admin)
    card = await api.get(f"{_company(world)}/changes/{original.id}", headers=headers)
    assert card.status_code == 200, card.text
    assert card.json()["access"] == "admin_read_only"
    assert card.json()["supersedes_number"] is None
    assert card.json()["superseded_by"] == [
        {"id": str(correction.id), "number": correction.number, "status": "draft"}
    ]
    linked = await api.get(
        f"{_company(world)}/changes/by-number/{correction.number}", headers=headers
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["supersedes_number"] == original.number
    assert linked.json()["superseded_by"] == []


async def test_members_card_access_is_member(api: AsyncClient, world: World) -> None:
    card = await api.get(_change(world), headers=auth(world.editor))
    assert card.status_code == 200
    assert card.json()["access"] == "member"
    assert set(card.json()["allowed_actions"]) == {"submit", "cancel"}
    viewer = await api.get(_change(world), headers=auth(world.viewer))
    assert viewer.json()["access"] == "member"
    assert viewer.json()["allowed_actions"] == []


async def test_admin_reads_the_card_of_another_company_only_under_its_own_path(
    api: AsyncClient, world: World
) -> None:
    assert world.draft_b is not None
    own = await api.get(
        f"{_company(world, world.b.id)}/changes/{world.draft_b.id}", headers=auth(world.admin)
    )
    assert own.status_code == 200, own.text
    assert own.json()["access"] == "admin_read_only"
    # B's change under A's path: 404 like a missing change (the scope holds only A).
    swapped = await api.get(
        f"{_company(world)}/changes/{world.draft_b.id}", headers=auth(world.admin)
    )
    missing = await api.get(f"{_company(world)}/changes/{uuid4()}", headers=auth(world.admin))
    assert_problem(swapped, 404, "change.not_found")
    assert_problem(missing, 404, "change.not_found")


async def test_admin_register_read_is_narrow_and_read_only(db_app: FastAPI, world: World) -> None:
    """The request transaction: only the target company in scope, no admin scope, READ
    ONLY - a write (even one RLS would allow) is rejected by PostgreSQL."""
    b_id = world.b.id
    assert world.draft_a is not None
    draft_id = world.draft_a.id
    author_id = world.editor.id

    @db_app.get("/test/probe-register-read/{company_id}")
    async def probe(
        session: SessionDep, ctx: CompanyContext = require_register_read()
    ) -> dict[str, Any]:
        async def scalar(sql: str, **params: Any) -> Any:
            return (await session.execute(text(sql), params)).scalar_one()

        own = await scalar("SELECT count(*) FROM changes WHERE company_id = :c", c=ctx.company_id)
        other = await scalar("SELECT count(*) FROM changes WHERE company_id = :c", c=b_id)
        settings = {
            name: await scalar("SELECT current_setting(:n, true)", n=name)
            for name in (
                "transaction_read_only",
                "app.company_ids",
                "app.admin_scope",
                "app.audit_global_read",
            )
        }
        try:
            async with session.begin_nested():
                await session.execute(
                    text(
                        "INSERT INTO change_comments "
                        "(id, company_id, change_id, author_id, body, created_at, updated_at) "
                        "VALUES (gen_random_uuid(), :c, :ch, :a, 'x', now(), now())"
                    ),
                    {"c": ctx.company_id, "ch": draft_id, "a": author_id},
                )
            error = ""
        except DBAPIError as exc:
            error = str(exc.orig)
        return {
            "own": own,
            "other": other,
            "settings": settings,
            "error": error,
            "read_only": ctx.read_only,
            "admin_path": ctx.admin_path,
        }

    async with client_for(db_app) as client:
        response = await client.get(
            f"/test/probe-register-read/{world.a.id}", headers=auth(world.admin)
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["own"] == 4
    assert body["other"] == 0
    assert body["settings"] == {
        "transaction_read_only": "on",
        "app.company_ids": "{" + str(world.a.id) + "}",
        "app.admin_scope": "off",
        "app.audit_global_read": "off",
    }
    assert "read-only transaction" in body["error"]
    assert body["read_only"] is True
    assert body["admin_path"] is True


# --------------------------------------------------------------------------- writes


async def test_admin_without_role_still_cannot_write_or_download(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    assert world.pending_a is not None
    assert world.attachment_a is not None
    headers = auth(world.admin)
    chain_before = await _company_chain_length(rw_engine, world.a.id)
    pending = f"{_company(world)}/changes/{world.pending_a.id}"
    attempts = [
        ("POST", f"{_company(world)}/changes", {"json": {"title": "Admin"}}),
        ("PATCH", _change(world), {"json": {"title": "Admin", "version": 1}}),
        ("POST", _change(world, "/comments"), {"json": {"body": "Admin"}}),
        (
            "POST",
            _change(world, "/attachments"),
            {"files": {"file": ("a.txt", b"admin", "text/plain")}},
        ),
        ("GET", _change(world, f"/attachments/{world.attachment_a.id}"), {}),
        *(
            ("POST", f"{_change(world)}/actions/{action}", {"json": {"comment": "Admin"}})
            for action in ("submit", "cancel", "consent")
        ),
        *(
            (
                "POST",
                f"{pending}/actions/{action}",
                {"json": {"comment": "Admin", "version": world.pending_a.version}},
            )
            for action in ("approve", "reject", "return")
        ),
    ]
    for method, url, kwargs in attempts:
        response = await api.request(method, url, headers=headers, **kwargs)
        assert_problem(response, 404, "company.not_found")
        (denial,) = await _denials(rw_engine, response)
        assert denial.actor_id == world.admin.id
        assert denial.context["status"] == 404
        assert denial.context["target_company_id"] == str(world.a.id)
    # Nothing written to the company: no change, comment, attachment, download entry.
    assert await _company_chain_length(rw_engine, world.a.id) == chain_before
    assert (await verify(rw_engine, world.a.id)).ok
    assert (await verify(rw_engine, None)).ok


# --------------------------------------------------------------------------- admin with a role


async def test_admin_with_a_role_keeps_the_normal_permissions(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    assert world.attachment_a is not None
    await grant(rw_engine, world.a, world.admin, Role.EDITOR)
    headers = auth(world.admin)
    created = await api.post(
        f"{_company(world)}/changes", json={"title": "Admin edytor"}, headers=headers
    )
    assert created.status_code == 201, created.text
    card = created.json()
    assert card["access"] == "member"
    assert set(card["allowed_actions"]) == {"submit", "cancel"}
    assert "title" in card["editable_fields"]
    again = await api.get(f"{_company(world)}/changes/{card['id']}", headers=headers)
    assert again.json()["access"] == "member"
    assert again.json()["allowed_actions"] == card["allowed_actions"]
    # The download works by membership and is audited in the company chain.
    before = await _company_chain_length(rw_engine, world.a.id)
    download = await api.get(
        _change(world, f"/attachments/{world.attachment_a.id}"), headers=headers
    )
    assert download.status_code == 200, download.text
    assert await _company_chain_length(rw_engine, world.a.id) == before + 1
    # Roles of the membership decide, not app_admin: an editor cannot approve.
    assert world.pending_a is not None
    approve = await api.post(
        f"{_company(world)}/changes/{world.pending_a.id}/actions/approve",
        json={"version": world.pending_a.version},
        headers=headers,
    )
    assert_problem(approve, 403, "auth.forbidden")


async def test_admin_viewer_reads_as_member(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    await grant(rw_engine, world.a, world.admin, Role.VIEWER)
    card = await api.get(_change(world), headers=auth(world.admin))
    assert card.status_code == 200
    assert card.json()["access"] == "member"
    assert card.json()["allowed_actions"] == []


# --------------------------------------------------------------------------- others, archive


async def test_auditor_or_anybody_without_membership_still_gets_404(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    foreign_auditor = await make_user(rw_engine, name="Audytor B")
    await grant(rw_engine, world.b, foreign_auditor, Role.AUDITOR)
    for user in (foreign_auditor, world.outsider, world.nobody):
        for url in (f"{_company(world)}/changes", _change(world), f"{_company(world)}/stats"):
            assert_problem(await api.get(url, headers=auth(user)), 404, "company.not_found")
    # The admin on a company that does not exist: 404 like everybody.
    assert_problem(
        await api.get(f"{_company(world, uuid4())}/changes", headers=auth(world.admin)),
        404,
        "company.not_found",
    )


async def test_archived_company_is_read_only_for_the_admin_like_for_members(
    api: AsyncClient, world: World
) -> None:
    archived = await api.post(f"{_company(world)}/archive", headers=auth(world.admin))
    assert archived.status_code == 200, archived.text
    for user in (world.admin, world.editor):
        listing = await api.get(f"{_company(world)}/changes", headers=auth(user))
        assert listing.status_code == 200
        assert listing.json()["total"] == 4
        card = await api.get(_change(world), headers=auth(user))
        assert card.status_code == 200
        assert card.json()["allowed_actions"] == []
        assert card.json()["editable_fields"] == []
    admin_card = await api.get(_change(world), headers=auth(world.admin))
    assert admin_card.json()["access"] == "admin_read_only"
    # Writes: the admin without a role - 404 (no membership), the editor - 409 archived.
    assert_problem(
        await api.post(
            f"{_company(world)}/changes", json={"title": "X"}, headers=auth(world.admin)
        ),
        404,
        "company.not_found",
    )
    assert_problem(
        await api.post(
            f"{_company(world)}/changes", json={"title": "X"}, headers=auth(world.editor)
        ),
        409,
        "company.archived",
    )
