"""Changes API (CLAUDE.md §4.1-4.3, §8; ADR 0012, ADR 0013): create, edit, readiness, the
transitions of §4.2 through HTTP, four eyes, standard auto-approval, emergency changes,
freezing, optimistic locking, register, card, stats and the change's audit trail.

The full transition matrix (status x type x actor) is tested on the pure domain
(``tests/test_change_state_machine.py``); here a representative set goes through the API,
the services and the database guards.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.changes import ChangeAction
from app.permissions import Role
from app.services import changes as changes_service
from tests.factories import (
    World,
    audit_entries,
    auth,
    change_actor,
    grant,
    make_available,
    make_category,
    make_change,
    make_ci,
    make_company,
    make_user,
    ready_values,
    scoped,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

NUMBER_RE = re.compile(r"^CHG-([A-Z]{2,8})-(\d{4})-(\d{4,})$")


def changes_url(company_id: UUID, change_id: UUID | None = None, suffix: str = "") -> str:
    base = f"/api/v1/companies/{company_id}/changes"
    if change_id is not None:
        base = f"{base}/{change_id}"
    return base + suffix


def jsonable(values: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, UUID):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, list):
            out[key] = [str(v) for v in value]
        else:
            out[key] = value
    return out


def ready_body(world: World, **overrides: Any) -> dict[str, Any]:
    return jsonable(
        ready_values(
            category=world.category,
            ci=[world.ci_a],
            assignee=world.editor,
            approver=world.approver,
            **overrides,
        )
    )


async def create(api: AsyncClient, world: World, who: Any, body: dict[str, Any]) -> Response:
    return await api.post(changes_url(world.a.id), json=body, headers=auth(who))


async def action(
    api: AsyncClient,
    world: World,
    change_id: str | UUID,
    name: str,
    who: Any,
    **body: Any,
) -> Response:
    if name == "approve" and "version" not in body:
        # approve needs the version the approver has seen (ADR 0013 §7)
        card = await api.get(changes_url(world.a.id, UUID(str(change_id))), headers=auth(who))
        if card.status_code == 200:
            body["version"] = card.json()["version"]
    return await api.post(
        changes_url(world.a.id, UUID(str(change_id)), f"/actions/{name}"),
        json=body or None,
        headers=auth(who),
    )


@pytest.fixture
async def available(world: World, rw_engine: AsyncEngine) -> World:
    """World with its category available in company A (readiness: category.available)."""
    await make_available(rw_engine, world.a, world.category)
    return world


async def ready_change(api: AsyncClient, world: World, **overrides: Any) -> dict[str, Any]:
    response = await create(api, world, world.editor, ready_body(world, **overrides))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


# --------------------------------------------------------------------------- create / read


async def test_editor_creates_a_draft_with_number_and_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await create(api, world, world.editor, {"title": "  Pierwszy szkic  "})
    assert response.status_code == 201, response.text
    body = response.json()
    match = NUMBER_RE.match(body["number"])
    assert match is not None
    assert match.group(1) == world.a.prefix
    assert int(match.group(3)) == 1  # first change of the company this year
    assert body["status"] == "draft"
    assert body["title"] == "Pierwszy szkic"
    assert body["requested_by"] == {"id": str(world.editor.id), "display_name": "Ewa Edytorska"}
    assert body["version"] == 1
    assert response.headers["ETag"] == '"1"'
    assert response.headers["Location"].endswith(body["id"])
    # submit is offered also to an incomplete draft (it explains what is missing, ADR 0012 §8)
    assert set(body["allowed_actions"]) == {"submit", "cancel"}
    assert "title" in body["editable_fields"]
    assert "ci_ids" in body["editable_fields"]
    assert body["created_at"].endswith("Z")

    entries = await audit_entries(rw_engine, UUID(body["id"]))
    assert [(e.action, e.company_id) for e in entries] == [("create", world.a.id)]
    assert entries[0].context == {"number": body["number"], "status": "draft", "version": 1}
    assert entries[0].diff["title"] == {"before": None, "after": "Pierwszy szkic"}
    assert entries[0].diff["requested_by_id"]["after"] == str(world.editor.id)
    assert (await verify(rw_engine, world.a.id)).ok

    second = await create(api, world, world.approver, {})
    second_number = NUMBER_RE.match(second.json()["number"])
    assert second_number is not None
    assert int(second_number.group(3)) == 2


async def test_submit_is_allowed_but_explained_until_ready(
    api: AsyncClient, available: World
) -> None:
    world = available
    draft = (await create(api, world, world.editor, {"title": "Niepełny"})).json()
    readiness = await api.get(
        changes_url(world.a.id, UUID(draft["id"]), "/readiness"), headers=auth(world.viewer)
    )
    assert readiness.status_code == 200
    report = readiness.json()
    assert report["ok"] is False
    failed = {c["code"] for c in report["checks"] if not c["ok"]}
    assert {"category.required", "ci.required", "assignee.required"} <= failed
    submit = await action(api, world, draft["id"], "submit", world.editor)
    assert_problem(submit, 422, "change.not_ready")
    assert "ci_ids" in submit.json()["fields"]
    assert any(c["code"] == "ci.required" for c in submit.json()["checks"])


async def test_default_approver_comes_from_the_category_override(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    from app.services import company_categories

    async with scoped(rw_engine, [world.a.id], admin_scope=True) as session:
        await company_categories.set_company_categories(
            session,
            actor=change_actor(world.admin, world.a).audit,
            company_id=world.a.id,
            assignments=[
                company_categories.Assignment(
                    category_id=world.category.id, approver_override_id=world.approver.id
                )
            ],
        )
    body = ready_body(world)
    del body["approver_id"]
    created = await create(api, world, world.editor, body)
    assert created.json()["approver"]["id"] == str(world.approver.id)
    # The requester is never suggested (four eyes): the approver creating it gets none.
    own = await create(api, world, world.approver, body)
    assert own.json()["approver"] is None


async def test_create_rejects_foreign_or_unknown_references(api: AsyncClient, world: World) -> None:
    foreign_ci = await create(api, world, world.editor, {"ci_ids": [str(world.ci_b.id)]})
    missing_ci = await create(api, world, world.editor, {"ci_ids": [str(uuid4())]})
    assert_problem(foreign_ci, 422, "change.ci_not_found")
    assert foreign_ci.json()["detail"] == missing_ci.json()["detail"]
    assert_problem(
        await create(api, world, world.editor, {"category_id": str(uuid4())}),
        422,
        "change.category_not_found",
    )
    assert_problem(
        await create(api, world, world.editor, {"assignee_id": str(uuid4())}),
        422,
        "change.user_not_found",
    )
    assert_problem(
        await create(api, world, world.editor, {"supersedes_change_id": str(uuid4())}),
        422,
        "change.supersedes_not_found",
    )
    # status / number / requested_by cannot be sent at all
    for field in ("status", "number", "requested_by_id", "version"):
        bad = await create(api, world, world.editor, {field: "approved"})
        assert_problem(bad, 422, "request.validation_error")
    reversed_window = await create(
        api,
        world,
        world.editor,
        {"window_start": "2030-01-02T10:00:00Z", "window_end": "2030-01-02T09:00:00Z"},
    )
    assert_problem(reversed_window, 422, "change.invalid_window")


async def test_card_by_id_and_number_and_register_filters(
    api: AsyncClient, available: World
) -> None:
    world = available
    first = await ready_change(api, world, title="Aktualizacja firmware przełącznika")
    second = await ready_change(api, world, title="Reguła NAT", change_type="emergency")
    by_number = await api.get(
        changes_url(world.a.id, None, f"/by-number/{first['number']}"), headers=auth(world.viewer)
    )
    assert by_number.status_code == 200, by_number.text
    assert by_number.json()["id"] == first["id"]
    assert by_number.json()["allowed_actions"] == []  # a viewer acts on nothing
    assert by_number.json()["editable_fields"] == []
    missing = await api.get(
        changes_url(world.a.id, None, "/by-number/CHG-ZZ-2026-9999"), headers=auth(world.viewer)
    )
    assert_problem(missing, 404, "change.not_found")

    listed = await api.get(changes_url(world.a.id), headers=auth(world.auditor))
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert [i["number"] for i in listed.json()["items"]] == [second["number"], first["number"]]
    item = listed.json()["items"][1]
    assert item["ci"][0]["identifier"] == world.ci_a.identifier
    assert item["category"]["code"] == world.category.code

    async def numbers(**params: Any) -> list[str]:
        response = await api.get(changes_url(world.a.id), params=params, headers=auth(world.viewer))
        assert response.status_code == 200, response.text
        return [i["number"] for i in response.json()["items"]]

    assert await numbers(q="firmware") == [first["number"]]
    assert await numbers(q=second["number"]) == [second["number"]]
    assert await numbers(type="emergency") == [second["number"]]
    assert await numbers(status=["draft", "approved"], sort="number") == [
        first["number"],
        second["number"],
    ]
    assert await numbers(status="approved") == []
    assert await numbers(ci=str(world.ci_a.id), limit=1, offset=1) == [first["number"]]
    assert await numbers(category=str(world.category.id), sort="-number") == [
        second["number"],
        first["number"],
    ]
    assert await numbers(assignee=str(world.editor.id), approver=str(world.approver.id)) != []
    assert await numbers(assignee=str(world.approver.id)) == []
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    assert await numbers(period_to=future, period_by="created") != []
    assert await numbers(period_from=future) == []
    assert await numbers(period_by="implemented", period_to=future) == []
    bad = await api.get(
        changes_url(world.a.id),
        params={"period_from": future, "period_to": future},
        headers=auth(world.viewer),
    )
    assert_problem(bad, 422, "change.invalid_period")


# --------------------------------------------------------------------------- transitions


async def test_normal_path_from_draft_to_verified(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world, verifier_id=str(world.approver.id))
    cid = change["id"]
    assert set(change["allowed_actions"]) == {"submit", "cancel"}

    submitted = await action(api, world, cid, "submit", world.editor)
    assert submitted.status_code == 200, submitted.text
    assert (submitted.json()["from_status"], submitted.json()["to_status"]) == (
        "draft",
        "pending_approval",
    )
    # The approver sees what they may do.
    card = await api.get(changes_url(world.a.id, UUID(cid)), headers=auth(world.approver))
    assert set(card.json()["allowed_actions"]) == {"approve", "reject", "return"}
    assert set(card.json()["editable_fields"]) == {"approver_id", "window_start", "window_end"}

    approved = await action(api, world, cid, "approve", world.approver)
    assert approved.json()["to_status"] == "approved"
    assert approved.json()["change"]["approved_at"] is not None

    implemented = await action(api, world, cid, "implement", world.editor)
    assert implemented.json()["to_status"] == "implemented"
    assert [w["code"] for w in implemented.json()["warnings"]] == ["implementation.outside_window"]
    ci = implemented.json()["change"]["ci"][0]
    assert ci["snapshot"] is True
    assert ci["identifier"] == world.ci_a.identifier

    # The CI is renamed later: the frozen change keeps the snapshot.
    renamed = await api.patch(
        f"/api/v1/companies/{world.a.id}/ci/{world.ci_a.id}",
        json={"identifier": "FW-NOWY", "name": "Nowa nazwa"},
        headers=auth(world.editor),
    )
    assert renamed.status_code == 200
    card = (await api.get(changes_url(world.a.id, UUID(cid)), headers=auth(world.viewer))).json()
    assert card["ci"][0]["identifier"] == world.ci_a.identifier
    assert card["ci"][0]["current_identifier"] == "FW-NOWY"
    # Implemented now, before its window (tomorrow): warning + deviation (owner decision).
    assert {d["kind"] for d in card["deviations"]} == {
        "implemented_not_verified",
        "implemented_outside_window",
    }

    verified = await action(api, world, cid, "verify", world.approver)
    assert verified.status_code == 200, verified.text
    assert verified.json()["change"]["status"] == "verified"
    assert [d["kind"] for d in verified.json()["change"]["deviations"]] == [
        "implemented_outside_window"
    ]

    entries = await audit_entries(rw_engine, UUID(cid))
    transitions = [
        (e.action, e.context.get("from_status"), e.context.get("to_status"), e.actor_id)
        for e in entries
    ]
    assert transitions == [
        ("create", None, None, world.editor.id),
        ("transition", "draft", "pending_approval", world.editor.id),
        ("transition", "pending_approval", "approved", world.approver.id),
        ("transition", "approved", "implemented", world.editor.id),
        ("transition", "implemented", "verified", world.approver.id),
    ]
    assert entries[2].diff["status"] == {"before": "pending_approval", "after": "approved"}
    assert set(entries[2].diff) == {"status", "approved_at", "approved_by_id"}
    assert all(e.context["number"] == change["number"] for e in entries)
    assert (await verify(rw_engine, world.a.id)).ok


async def test_frozen_change_cannot_be_edited(api: AsyncClient, available: World) -> None:
    world = available
    change = await ready_change(api, world)
    cid = change["id"]
    for name, who in (("submit", world.editor), ("approve", world.approver)):
        assert (await action(api, world, cid, name, who)).status_code == 200
    approved = (
        await api.get(changes_url(world.a.id, UUID(cid)), headers=auth(world.editor))
    ).json()
    edit_approved = await api.patch(
        changes_url(world.a.id, UUID(cid)),
        json={"title": "Zmiana po zatwierdzeniu", "version": approved["version"]},
        headers=auth(world.editor),
    )
    assert_problem(edit_approved, 422, "change.field_not_editable")
    implemented = await action(api, world, cid, "implement", world.editor)
    frozen = await api.patch(
        changes_url(world.a.id, UUID(cid)),
        json={"title": "Korekta", "version": implemented.json()["change"]["version"]},
        headers=auth(world.editor),
    )
    assert_problem(frozen, 409, "change.frozen")
    # A correction is a NEW change pointing to the original.
    correction = await create(
        api, world, world.editor, {"title": "Korekta", "supersedes_change_id": cid}
    )
    assert correction.status_code == 201
    assert correction.json()["supersedes_change_id"] == cid


async def test_correction_links_both_ways(api: AsyncClient, available: World) -> None:
    """ADR 0021: the correction shows the original's number, the original lists its
    corrections (oldest first) - on every response carrying the card."""
    world = available
    original = await ready_change(api, world)
    oid = original["id"]
    assert original["supersedes_number"] is None
    assert original["superseded_by"] == []

    first = await create(
        api, world, world.editor, {"title": "Korekta 1", "supersedes_change_id": oid}
    )
    assert first.status_code == 201, first.text
    assert first.json()["supersedes_change_id"] == oid
    assert first.json()["supersedes_number"] == original["number"]
    assert first.json()["superseded_by"] == []
    second = await create(
        api, world, world.editor, {"title": "Korekta 2", "supersedes_change_id": oid}
    )
    assert second.status_code == 201
    cancelled = await action(api, world, second.json()["id"], "cancel", world.editor)
    assert cancelled.status_code == 200, cancelled.text
    # A correction of the correction belongs to the correction, not to the original.
    nested = await create(
        api,
        world,
        world.editor,
        {"title": "Korekta 1b", "supersedes_change_id": first.json()["id"]},
    )
    assert nested.json()["supersedes_number"] == first.json()["number"]

    expected = [
        {"id": first.json()["id"], "number": first.json()["number"], "status": "draft"},
        {"id": second.json()["id"], "number": second.json()["number"], "status": "cancelled"},
    ]
    card = await api.get(changes_url(world.a.id, UUID(oid)), headers=auth(world.viewer))
    assert card.status_code == 200
    assert card.json()["superseded_by"] == expected
    assert card.json()["supersedes_number"] is None
    by_number = await api.get(
        changes_url(world.a.id, suffix=f"/by-number/{original['number']}"),
        headers=auth(world.auditor),
    )
    assert by_number.json()["superseded_by"] == expected
    patched = await api.patch(
        changes_url(world.a.id, UUID(oid)),
        json={"title": "Oryginał", "version": card.json()["version"]},
        headers=auth(world.editor),
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["superseded_by"] == expected
    submitted = await action(api, world, oid, "submit", world.editor)
    assert submitted.json()["change"]["superseded_by"] == expected
    child = await api.get(
        changes_url(world.a.id, UUID(first.json()["id"])), headers=auth(world.viewer)
    )
    assert child.json()["superseded_by"] == [
        {"id": nested.json()["id"], "number": nested.json()["number"], "status": "draft"}
    ]

    # Isolation: B's member does not see A's card; the register rows carry no links.
    outsider = await api.get(changes_url(world.a.id, UUID(oid)), headers=auth(world.outsider))
    assert_problem(outsider, 404, "company.not_found")
    listing = await api.get(changes_url(world.a.id), headers=auth(world.viewer))
    assert all("superseded_by" not in row for row in listing.json()["items"])


async def test_four_eyes_through_the_api(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    second_approver = await make_user(rw_engine, name="Zofia Zatwierdzająca")
    await grant(rw_engine, world.a, second_approver, Role.APPROVER)
    # Created by the second approver, designated approver: the first one.
    body = ready_body(world)
    created = await create(api, world, second_approver, body)
    cid = created.json()["id"]
    assert (await action(api, world, cid, "submit", world.editor)).status_code == 200
    # The requester cannot approve (four eyes) - also not by re-assigning to themselves.
    own = await action(api, world, cid, "approve", second_approver)
    assert_problem(own, 403, "change.four_eyes_violation")
    version = created.json()["version"] + 1
    reassign = await api.patch(
        changes_url(world.a.id, UUID(cid)),
        json={"approver_id": str(second_approver.id), "version": version},
        headers=auth(second_approver),
    )
    assert_problem(reassign, 403, "change.forbidden_actor")
    # An editor has no approve right at all (matrix), the designated approver has.
    assert_problem(await action(api, world, cid, "approve", world.editor), 403, "auth.forbidden")
    assert (await action(api, world, cid, "approve", world.approver)).status_code == 200

    # Readiness refuses a change whose designated approver is its assignee.
    selfish = ready_body(world, assignee_id=world.approver.id)
    draft = await create(api, world, world.approver, selfish)
    submit = await action(api, world, draft.json()["id"], "submit", world.approver)
    assert_problem(submit, 422, "change.not_ready")
    assert "approver.four_eyes" in {c["code"] for c in submit.json()["checks"] if not c["ok"]}


async def test_reject_return_rollback_and_cancel_need_the_right_comment(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    rejected = await ready_change(api, world)
    await action(api, world, rejected["id"], "submit", world.editor)
    no_comment = await action(api, world, rejected["id"], "reject", world.approver)
    assert_problem(no_comment, 422, "change.comment_required")
    blank = await action(api, world, rejected["id"], "reject", world.approver, comment="   ")
    assert_problem(blank, 422, "change.comment_required")
    too_long = await action(
        api, world, rejected["id"], "reject", world.approver, comment="x" * 4001
    )
    assert_problem(too_long, 422, "change.comment_too_long")
    done = await action(
        api, world, rejected["id"], "reject", world.approver, comment="Brak planu wycofania."
    )
    assert done.status_code == 200
    card = done.json()["change"]
    assert card["status"] == "rejected"
    assert card["rejected_at"] is not None
    assert [(c["action"], c["body"]) for c in card["comments"]] == [
        ("reject", "Brak planu wycofania.")
    ]
    entry = (await audit_entries(rw_engine, UUID(rejected["id"])))[-1]
    assert entry.context["comment"] == "Brak planu wycofania."
    assert entry.context["comment_id"] == card["comments"][0]["id"]
    # rejected is terminal and frozen
    assert_problem(
        await action(api, world, rejected["id"], "submit", world.editor),
        409,
        "change.invalid_transition",
    )

    returned = await ready_change(api, world)
    await action(api, world, returned["id"], "submit", world.editor)
    back = await action(
        api, world, returned["id"], "return", world.approver, comment="Uzupełnij wpływ."
    )
    assert back.json()["to_status"] == "draft"
    # back in draft: every editor/approver of the company edits it again (§5)
    assert "title" in back.json()["change"]["editable_fields"]
    again = await action(api, world, returned["id"], "submit", world.editor)
    assert again.json()["to_status"] == "pending_approval"

    rolled = await ready_change(api, world)
    for name, who in (
        ("submit", world.editor),
        ("approve", world.approver),
        ("implement", world.editor),
    ):
        assert (await action(api, world, rolled["id"], name, who)).status_code == 200
    assert_problem(
        await action(api, world, rolled["id"], "rollback", world.editor),
        422,
        "change.comment_required",
    )
    rollback = await action(
        api, world, rolled["id"], "rollback", world.approver, comment="Błąd po wdrożeniu."
    )
    assert rollback.json()["to_status"] == "rolled_back"
    assert {d["kind"] for d in rollback.json()["change"]["deviations"]} == {
        "rolled_back",
        "implemented_outside_window",
    }

    cancelled = await ready_change(api, world)
    assert_problem(
        await action(api, world, cancelled["id"], "cancel", world.approver),
        403,
        "change.forbidden_actor",
    )
    cancel = await action(api, world, cancelled["id"], "cancel", world.editor)
    assert cancel.json()["to_status"] == "cancelled"
    assert (await verify(rw_engine, world.a.id)).ok


async def test_unknown_action_and_version_on_actions(api: AsyncClient, available: World) -> None:
    world = available
    change = await ready_change(api, world)
    unknown = await action(api, world, change["id"], "teleport", world.editor)
    assert_problem(unknown, 404, "change.unknown_action")
    stale = await action(api, world, change["id"], "submit", world.editor, version=99)
    assert_problem(stale, 409, "change.version_conflict")
    assert stale.json()["current_version"] == 1
    ok = await action(api, world, change["id"], "submit", world.editor, version=1)
    assert ok.json()["change"]["version"] == 2


async def test_standard_change_is_approved_by_system(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    standard = await make_category(rw_engine, requires_approval=False)
    await make_available(rw_engine, world.a, standard)
    change = await ready_change(
        api, world, category_id=str(standard.id), change_type="standard", risk="low"
    )
    submitted = await action(api, world, change["id"], "submit", world.editor)
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["to_status"] == "approved"
    assert submitted.json()["performed_by_system"] is True
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert (entry.actor_id, entry.actor_display, entry.actor_roles) == (None, "system", [])
    assert entry.context["auto_approved"] is True
    assert entry.context["triggered_by"] == str(world.editor.id)
    assert entry.context["reason"] == "standard_change_without_approval"
    assert entry.diff["status"] == {"before": "draft", "after": "approved"}

    # The same category with a normal change goes through the approver.
    normal = await ready_change(api, world, category_id=str(standard.id))
    assert (await action(api, world, normal["id"], "submit", world.editor)).json()[
        "to_status"
    ] == "pending_approval"


async def test_emergency_change_and_the_24h_deviation(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    past = datetime.now(UTC) - timedelta(hours=40)
    change = await ready_change(
        api,
        world,
        change_type="emergency",
        risk="high",
        window_start=past,
        window_end=past + timedelta(hours=1),
        verifier_id=str(world.approver.id),
    )
    cid = UUID(change["id"])
    # Implemented 30 h ago through the service clock (the API clock is the database's).
    async with scoped(rw_engine, [world.a.id]) as session:
        await changes_service.perform_action(
            session,
            actor=change_actor(world.editor, world.a, Role.EDITOR),
            company=world.a,
            change_id=cid,
            action=ChangeAction.IMPLEMENT,
            now=datetime.now(UTC) - timedelta(hours=30),
        )
    card = (await api.get(changes_url(world.a.id, cid), headers=auth(world.viewer))).json()
    assert card["status"] == "implemented"
    assert card["approved_at"] is None
    assert {d["kind"] for d in card["deviations"]} == {
        "emergency_not_approved_in_24h",
        "implemented_not_verified",
    }
    stats = await api.get(f"/api/v1/companies/{world.a.id}/stats", headers=auth(world.viewer))
    assert stats.json()["emergency_not_approved_in_24h"] == 1
    assert stats.json()["emergency_last_30_days"] == 1
    assert stats.json()["implemented_not_verified"] == 1

    # Verification waits for the after-the-fact approval.
    assert_problem(
        await action(api, world, cid, "verify", world.approver), 409, "change.approval_missing"
    )
    late = await action(api, world, cid, "approve", world.approver)
    assert late.status_code == 200, late.text
    assert (late.json()["from_status"], late.json()["to_status"]) == ("implemented", "implemented")
    assert [w["code"] for w in late.json()["warnings"]] == ["emergency.approval_late"]
    entry = (await audit_entries(rw_engine, cid))[-1]
    assert entry.action == "transition"
    assert entry.context["action"] == "approve"
    assert entry.context["warnings"][0]["code"] == "emergency.approval_late"
    # The late approval does not remove the deviation.
    card = late.json()["change"]
    assert "emergency_not_approved_in_24h" in {d["kind"] for d in card["deviations"]}
    assert (await action(api, world, cid, "verify", world.approver)).status_code == 200

    # Emergency implemented now: approval due within 24 h is recorded in the audit context.
    fresh = await ready_change(api, world, change_type="emergency")
    done = await action(api, world, fresh["id"], "implement", world.editor)
    assert done.status_code == 200, done.text
    entry = (await audit_entries(rw_engine, UUID(fresh["id"])))[-1]
    assert entry.context["approval_due_at"].endswith("Z")


async def test_ci_owner_consent_before_approval(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    ot = await make_category(rw_engine, requires_ci_owner_consent=True, default_risk="high")
    await make_available(rw_engine, world.a, ot)
    plc = await make_ci(rw_engine, world.a, world.ci_type, owner_user_id=world.viewer.id)
    change = await ready_change(api, world, category_id=str(ot.id), ci_ids=[plc.id])
    cid = change["id"]
    assert (await action(api, world, cid, "submit", world.editor)).status_code == 200
    missing = await action(api, world, cid, "approve", world.approver)
    assert_problem(missing, 409, "change.ci_owner_consent_missing")
    assert plc.identifier in missing.json()["detail"]
    # Only the owner consents (any role - here a viewer).
    assert_problem(
        await action(api, world, cid, "consent", world.auditor), 403, "change.forbidden_actor"
    )
    consent = await action(api, world, cid, "consent", world.viewer, comment="Zgoda UR.")
    assert consent.status_code == 200, consent.text
    card = consent.json()["change"]
    assert card["status"] == "pending_approval"
    assert card["ci"][0]["consented"] is True
    assert card["consents"][0]["owner"]["id"] == str(world.viewer.id)
    again = await action(api, world, cid, "consent", world.viewer)
    assert_problem(again, 409, "change.invalid_transition")
    entry = (await audit_entries(rw_engine, UUID(cid)))[-1]
    assert (entry.action, entry.context["action"]) == ("transition", "consent")
    assert entry.context["from_status"] == entry.context["to_status"] == "pending_approval"
    assert entry.context["consented_ci_ids"] == [str(plc.id)]
    assert entry.diff == {}

    # return starts a new consent round
    back = await action(api, world, cid, "return", world.approver, comment="Popraw okno.")
    assert back.json()["change"]["consents"] == []
    await action(api, world, cid, "submit", world.editor)
    assert_problem(
        await action(api, world, cid, "approve", world.approver),
        409,
        "change.ci_owner_consent_missing",
    )
    await action(api, world, cid, "consent", world.viewer)
    assert (await action(api, world, cid, "approve", world.approver)).status_code == 200


# --------------------------------------------------------------------------- editing


async def test_patch_needs_the_current_version(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    url = changes_url(world.a.id, UUID(change["id"]))
    missing = await api.patch(url, json={"title": "Bez wersji"}, headers=auth(world.editor))
    assert_problem(missing, 428, "change.version_required")
    via_header = await api.patch(
        url, json={"title": "Przez If-Match"}, headers={**auth(world.editor), "If-Match": '"1"'}
    )
    assert via_header.status_code == 200, via_header.text
    assert via_header.json()["version"] == 2
    assert via_header.headers["ETag"] == '"2"'
    stale = await api.patch(url, json={"title": "Stara", "version": 1}, headers=auth(world.editor))
    assert_problem(stale, 409, "change.version_conflict")
    assert stale.json()["current_version"] == 2
    mismatch = await api.patch(
        url, json={"title": "X", "version": 2}, headers={**auth(world.editor), "If-Match": '"3"'}
    )
    assert_problem(mismatch, 400, "change.version_mismatch")
    garbage = await api.patch(
        url, json={"title": "X"}, headers={**auth(world.editor), "If-Match": "abc"}
    )
    assert_problem(garbage, 400, "change.invalid_if_match")

    # Nothing changed: no new version, no audit entry.
    before = len(await audit_entries(rw_engine, UUID(change["id"])))
    same = await api.patch(
        url, json={"title": "Przez If-Match", "version": 2}, headers=auth(world.editor)
    )
    assert same.json()["version"] == 2
    assert len(await audit_entries(rw_engine, UUID(change["id"]))) == before

    # Another editor of the company edits the draft too (§5), with an audited diff.
    other_ci = await make_ci(rw_engine, world.a, world.ci_type)
    edited = await api.patch(
        url,
        json={"ci_ids": [str(world.ci_a.id), str(other_ci.id)], "impact": " Brak ", "version": 2},
        headers=auth(world.approver),
    )
    assert edited.status_code == 200, edited.text
    assert {c["id"] for c in edited.json()["ci"]} == {str(world.ci_a.id), str(other_ci.id)}
    assert edited.json()["impact"] == "Brak"
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert entry.action == "update"
    assert set(entry.diff) == {"ci_ids", "impact"}
    assert entry.diff["ci_ids"]["after"] == sorted([str(world.ci_a.id), str(other_ci.id)])
    assert entry.context == {"number": change["number"], "status": "draft", "version": 3}

    # Read-only roles cannot edit at all.
    assert_problem(
        await api.patch(url, json={"title": "X", "version": 3}, headers=auth(world.viewer)),
        403,
        "auth.forbidden",
    )


async def test_pending_approval_edits_by_an_approver_only(
    api: AsyncClient, available: World
) -> None:
    world = available
    change = await ready_change(api, world)
    submitted = await action(api, world, change["id"], "submit", world.editor)
    version = submitted.json()["change"]["version"]
    url = changes_url(world.a.id, UUID(change["id"]))
    by_editor = await api.patch(
        url, json={"title": "Nowy", "version": version}, headers=auth(world.editor)
    )
    assert_problem(by_editor, 403, "change.forbidden_actor")
    title = await api.patch(
        url, json={"title": "Nowy", "version": version}, headers=auth(world.approver)
    )
    assert_problem(title, 422, "change.field_not_editable")
    assert title.json()["fields"] == ["title"]
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    window = await api.patch(
        url, json={"window_start": past, "version": version}, headers=auth(world.approver)
    )
    assert_problem(window, 422, "change.invalid_edit")
    assert "window.future" in {c["code"] for c in window.json()["checks"]}
    later = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    later_end = (datetime.now(UTC) + timedelta(days=3, hours=1)).isoformat()
    moved = await api.patch(
        url,
        json={"window_start": later, "window_end": later_end, "version": version},
        headers=auth(world.approver),
    )
    assert moved.status_code == 200, moved.text


async def test_concurrent_patches_one_wins_one_conflicts(
    api: AsyncClient, available: World
) -> None:
    world = available
    change = await ready_change(api, world)
    url = changes_url(world.a.id, UUID(change["id"]))
    responses = await asyncio.gather(
        *(
            api.patch(url, json={"title": f"Wersja {i}", "version": 1}, headers=auth(world.editor))
            for i in range(4)
        )
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409, 409, 409]
    for response in responses:
        if response.status_code == 409:
            assert_problem(response, 409, "change.version_conflict")


async def test_concurrent_creates_get_consecutive_unique_numbers(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    company = await make_company(rw_engine)
    await grant(rw_engine, company, world.editor, Role.EDITOR)
    url = changes_url(company.id)
    responses = await asyncio.gather(
        *(
            api.post(url, json={"title": f"Równolegle {i}"}, headers=auth(world.editor))
            for i in range(12)
        )
    )
    assert {r.status_code for r in responses} == {201}, [r.text for r in responses]
    numbers = sorted(int(NUMBER_RE.match(r.json()["number"]).group(3)) for r in responses)  # type: ignore[union-attr]
    assert numbers == list(range(1, 13))
    assert (await verify(rw_engine, company.id)).ok


async def test_numbering_year_is_warsaw_local(rw_engine: AsyncEngine, world: World) -> None:
    """31.12 23:30 UTC is already 1 January in Warsaw: the new year's counter starts."""
    from app.services import numbering

    company = await make_company(rw_engine)
    async with scoped(rw_engine, [company.id]) as session:
        new_year = datetime(2030, 12, 31, 23, 30, tzinfo=UTC)
        old_year = datetime(2030, 12, 31, 22, 30, tzinfo=UTC)
        assert await numbering.numbering_year(session, new_year) == 2031
        assert await numbering.numbering_year(session, old_year) == 2030
        first = await numbering.next_number(
            session, company_id=company.id, prefix=company.prefix, at=new_year
        )
        second = await numbering.next_number(
            session, company_id=company.id, prefix=company.prefix, at=new_year
        )
        other = await numbering.next_number(
            session, company_id=company.id, prefix=company.prefix, at=old_year
        )
    assert first == f"CHG-{company.prefix}-2031-0001"
    assert second == f"CHG-{company.prefix}-2031-0002"
    assert other == f"CHG-{company.prefix}-2030-0001"
    assert numbering.format_number("ALFA", 2026, 12345) == "CHG-ALFA-2026-12345"


# --------------------------------------------------------------------------- company archive


async def test_archived_company_changes_are_read_only(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    archived = await api.post(f"/api/v1/companies/{world.a.id}/archive", headers=auth(world.admin))
    assert archived.status_code == 200
    url = changes_url(world.a.id, UUID(change["id"]))
    assert_problem(await create(api, world, world.editor, {}), 409, "company.archived")
    assert_problem(
        await api.patch(url, json={"title": "X", "version": 1}, headers=auth(world.editor)),
        409,
        "company.archived",
    )
    assert_problem(
        await action(api, world, change["id"], "submit", world.editor), 409, "company.archived"
    )
    assert_problem(
        await api.post(f"{url}/comments", json={"body": "Uwaga"}, headers=auth(world.editor)),
        409,
        "company.archived",
    )
    card = await api.get(url, headers=auth(world.editor))
    assert card.status_code == 200
    assert card.json()["allowed_actions"] == []
    assert card.json()["editable_fields"] == []


async def test_change_write_racing_an_archive_is_rejected(
    rw_engine: AsyncEngine, world: World
) -> None:
    """The service check reads a stale company; the trigger (FOR SHARE) waits for the
    archive and refuses the INSERT - 409, no change, no number used up."""
    from app.services import companies
    from tests.factories import SYSTEM

    company = await make_company(rw_engine)
    await grant(rw_engine, company, world.editor, Role.EDITOR)
    started = asyncio.Event()

    async def archive() -> None:
        async with scoped(rw_engine, [company.id], admin_scope=True) as session:
            await companies.archive_company(session, actor=SYSTEM, company_id=company.id)
            started.set()
            await asyncio.sleep(0.5)

    async def write() -> Any:
        await started.wait()
        try:
            await make_change(rw_engine, company, world.editor, Role.EDITOR)
        except Exception as exc:
            return exc
        return None

    _, error = await asyncio.gather(archive(), write())
    assert error is not None
    assert (error.status, error.code) == (409, "company.archived")
    async with scoped(rw_engine, [company.id]) as session:
        page = await changes_service.list_changes(
            session, company.id, changes_service.ChangeFilters(), limit=10, offset=0
        )
    assert page.total == 0


# --------------------------------------------------------------------------- comments, audit


async def test_comments_and_the_change_audit_trail(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    url = changes_url(world.a.id, UUID(change["id"]))
    comment = await api.post(
        f"{url}/comments", json={"body": "  Proszę o okno w nocy.  "}, headers=auth(world.approver)
    )
    assert comment.status_code == 201, comment.text
    assert comment.json()["body"] == "Proszę o okno w nocy."
    assert comment.json()["author"]["id"] == str(world.approver.id)
    assert_problem(
        await api.post(f"{url}/comments", json={"body": "  "}, headers=auth(world.editor)),
        422,
        "change.comment_required",
    )
    assert_problem(
        await api.post(f"{url}/comments", json={"body": "Hej"}, headers=auth(world.viewer)),
        403,
        "auth.forbidden",
    )
    upload = await api.post(
        f"{url}/attachments",
        files={"file": ("plan.txt", b"plan wdrozenia", "text/plain")},
        headers=auth(world.editor),
    )
    assert upload.status_code == 201, upload.text
    await action(api, world, change["id"], "submit", world.editor)

    trail = await api.get(f"{url}/audit", headers=auth(world.viewer))
    assert trail.status_code == 200, trail.text
    items = trail.json()["items"]
    assert [(i["entity_type"], i["action"]) for i in items] == [
        ("change", "create"),
        ("change", "comment"),
        ("attachment", "attach"),
        ("change", "transition"),
    ]
    assert trail.json()["total"] == 4
    assert all(i["hash_valid"] for i in items)
    assert [i["seq"] for i in items] == sorted(i["seq"] for i in items)
    assert items[1]["context"]["comment"] == "Proszę o okno w nocy."
    assert items[2]["context"]["sha256"] == upload.json()["sha256"]
    card = (await api.get(url, headers=auth(world.viewer))).json()
    assert [c["body"] for c in card["comments"]] == ["Proszę o okno w nocy."]
    page = await api.get(
        f"{url}/audit", params={"limit": 2, "offset": 2}, headers=auth(world.viewer)
    )
    assert [i["action"] for i in page.json()["items"]] == ["attach", "transition"]


async def test_stats_tiles(api: AsyncClient, available: World) -> None:
    world = available
    pending = await ready_change(api, world)
    await action(api, world, pending["id"], "submit", world.editor)
    approved = await ready_change(api, world)
    await action(api, world, approved["id"], "submit", world.editor)
    await action(api, world, approved["id"], "approve", world.approver)
    await ready_change(api, world)
    stats = await api.get(f"/api/v1/companies/{world.a.id}/stats", headers=auth(world.viewer))
    assert stats.status_code == 200
    assert stats.json() == {
        "pending_approval": 1,
        "approved_not_implemented": 1,
        "emergency_last_30_days": 0,
        "implemented_not_verified": 0,
        "emergency_not_approved_in_24h": 0,
        "implemented_outside_window": 0,
        "by_status": {"draft": 1, "pending_approval": 1, "approved": 1},
    }


# --------------------------------------------------------------------------- owner decisions


async def test_approved_change_can_be_cancelled_with_a_comment(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    await action(api, world, change["id"], "submit", world.editor)
    await action(api, world, change["id"], "approve", world.approver)
    no_comment = await action(api, world, change["id"], "cancel", world.approver)
    assert_problem(no_comment, 422, "change.comment_required")
    cancelled = await action(
        api, world, change["id"], "cancel", world.approver, comment="Nieaktualna."
    )
    assert cancelled.status_code == 200, cancelled.text
    assert (cancelled.json()["from_status"], cancelled.json()["to_status"]) == (
        "approved",
        "cancelled",
    )
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert entry.context["comment"] == "Nieaktualna."
    assert (await verify(rw_engine, world.a.id)).ok


async def test_implementation_outside_the_window_is_a_warning_and_a_deviation(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    for name, who in (("submit", world.editor), ("approve", world.approver)):
        await action(api, world, change["id"], name, who)
    done = await action(api, world, change["id"], "implement", world.editor)
    assert [w["code"] for w in done.json()["warnings"]] == ["implementation.outside_window"]
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert [w["code"] for w in entry.context["warnings"]] == ["implementation.outside_window"]
    stats = await api.get(f"/api/v1/companies/{world.a.id}/stats", headers=auth(world.viewer))
    assert stats.json()["implemented_outside_window"] == 1


async def test_verifier_of_an_implemented_change_can_be_re_pointed(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    """The designated verifier lost their role: an approver re-points it (ADR 0012 §6)."""
    world = available
    leaving = await make_user(rw_engine, name="Odchodzący Weryfikujący")
    await grant(rw_engine, world.a, leaving, Role.EDITOR)
    change = await ready_change(api, world, verifier_id=str(leaving.id))
    for name, who in (
        ("submit", world.editor),
        ("approve", world.approver),
        ("implement", world.editor),
    ):
        assert (await action(api, world, change["id"], name, who)).status_code == 200
    url = changes_url(world.a.id, UUID(change["id"]))
    card = (await api.get(url, headers=auth(world.approver))).json()
    blocked = await api.patch(
        url,
        json={"verifier_id": str(world.approver.id), "version": card["version"]},
        headers=auth(world.approver),
    )
    assert_problem(blocked, 409, "change.frozen")  # the verifier can still verify
    await grant(rw_engine, world.a, leaving)  # all roles revoked
    card = (await api.get(url, headers=auth(world.approver))).json()
    assert card["editable_fields"] == ["verifier_id"]
    moved = await api.patch(
        url,
        json={"verifier_id": str(world.approver.id), "version": card["version"]},
        headers=auth(world.approver),
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["verifier"]["id"] == str(world.approver.id)
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert (entry.action, set(entry.diff)) == ("update", {"verifier_id"})
    assert (await action(api, world, change["id"], "verify", world.approver)).status_code == 200


# --------------------------------------------------------------------------- review fixes


async def test_the_approver_of_record_is_who_approved(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """Standard auto-approval: approved by ``system``, not by the designated approver."""
    standard = await make_category(rw_engine, requires_approval=False)
    await make_available(rw_engine, world.a, standard, world.category)
    auto = await ready_change(
        api, world, category_id=str(standard.id), change_type="standard", risk="low"
    )
    done = (await action(api, world, auto["id"], "submit", world.editor)).json()["change"]
    assert done["approver"]["id"] == str(world.approver.id)  # designated only
    assert (done["approved_by"], done["auto_approved"]) == (None, True)
    listed = await api.get(changes_url(world.a.id), headers=auth(world.viewer))
    row = next(i for i in listed.json()["items"] if i["id"] == auto["id"])
    assert (row["approved_by"], row["auto_approved"]) == (None, True)

    normal = await ready_change(api, world)
    await action(api, world, normal["id"], "submit", world.editor)
    approved = (await action(api, world, normal["id"], "approve", world.approver)).json()
    card = approved["change"]
    assert card["approved_by"] == {
        "id": str(world.approver.id),
        "display_name": "Jan Zatwierdzający",
    }
    assert card["auto_approved"] is False
    entry = (await audit_entries(rw_engine, UUID(normal["id"])))[-1]
    assert entry.diff["approved_by_id"] == {"before": None, "after": str(world.approver.id)}


async def test_approve_requires_the_seen_version(api: AsyncClient, available: World) -> None:
    world = available
    change = await ready_change(api, world)
    submitted = await action(api, world, change["id"], "submit", world.editor)
    version = submitted.json()["change"]["version"]
    url = changes_url(world.a.id, UUID(change["id"]), "/actions/approve")
    missing = await api.post(url, headers=auth(world.approver))
    assert_problem(missing, 428, "change.version_required")
    stale_tag = '"' + str(version - 1) + '"'
    current_tag = '"' + str(version) + '"'
    stale = await api.post(url, headers={**auth(world.approver), "If-Match": stale_tag})
    assert_problem(stale, 409, "change.version_conflict")
    ok = await api.post(url, headers={**auth(world.approver), "If-Match": current_tag})
    assert ok.status_code == 200, ok.text
    # other actions accept If-Match too, but do not require it
    implement = changes_url(world.a.id, UUID(change["id"]), "/actions/implement")
    wrong = await api.post(implement, headers={**auth(world.editor), "If-Match": '"1"'})
    assert_problem(wrong, 409, "change.version_conflict")
    assert (await api.post(implement, headers=auth(world.editor))).status_code == 200


async def test_people_must_be_members_of_the_company(api: AsyncClient, world: World) -> None:
    unknown = await create(api, world, world.editor, {"assignee_id": str(uuid4())})
    assert_problem(unknown, 422, "change.user_not_found")
    for user in (world.outsider, world.nobody):
        response = await create(api, world, world.editor, {"assignee_id": str(user.id)})
        assert_problem(response, 422, "change.user_not_found")
        assert response.json()["detail"] == unknown.json()["detail"]
    ok = await create(api, world, world.editor, {"verifier_id": str(world.viewer.id)})
    assert ok.status_code == 201  # eligibility (role) is readiness's job


async def _ot_change(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> tuple[dict[str, Any], Any]:
    ot = await make_category(rw_engine, requires_ci_owner_consent=True, default_risk="high")
    await make_available(rw_engine, world.a, ot)
    plc = await make_ci(rw_engine, world.a, world.ci_type, owner_user_id=world.viewer.id)
    change = await ready_change(api, world, category_id=str(ot.id), ci_ids=[plc.id])
    assert (await action(api, world, change["id"], "submit", world.editor)).status_code == 200
    return change, plc


async def test_ci_owner_cannot_be_switched_while_a_change_waits(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """The requester cannot make themselves the owner and consent to their own change."""
    change, plc = await _ot_change(api, world, rw_engine)
    ci_url = f"/api/v1/companies/{world.a.id}/ci/{plc.id}"
    me = {"owner_user_id": str(world.editor.id)}
    switch = await api.patch(ci_url, json=me, headers=auth(world.editor))
    assert_problem(switch, 409, "ci.owner_locked_by_change")
    assert switch.json()["changes"] == [change["number"]]
    # other CI fields stay editable
    renamed = await api.patch(ci_url, json={"name": "PLC linii 1"}, headers=auth(world.editor))
    assert renamed.status_code == 200
    # after the decision the owner can change again
    await action(api, world, change["id"], "consent", world.viewer)
    await action(api, world, change["id"], "approve", world.approver)
    moved = await api.patch(ci_url, json=me, headers=auth(world.editor))
    assert moved.status_code == 200, moved.text


async def test_consent_of_a_former_owner_does_not_count(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """Defence in depth: even if the owner changed outside the service (here: SQL as
    app_rw), only a consent of the CURRENT owner counts at approval."""
    from sqlalchemy import text

    change, plc = await _ot_change(api, world, rw_engine)
    assert (await action(api, world, change["id"], "consent", world.viewer)).status_code == 200
    async with scoped(rw_engine, [world.a.id]) as session:
        await session.execute(
            text("UPDATE configuration_items SET owner_user_id = :u WHERE id = :ci"),
            {"u": world.auditor.id, "ci": plc.id},
        )
    card_url = changes_url(world.a.id, UUID(change["id"]))
    card = (await api.get(card_url, headers=auth(world.approver))).json()
    assert card["consents"][0]["valid"] is False
    assert card["ci"][0]["consented"] is False
    missing = await action(api, world, change["id"], "approve", world.approver)
    assert_problem(missing, 409, "change.ci_owner_consent_missing")
    assert (await action(api, world, change["id"], "consent", world.auditor)).status_code == 200
    assert (await action(api, world, change["id"], "approve", world.approver)).status_code == 200


async def test_emergency_approver_who_left_can_be_re_pointed(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    leaving = await make_user(rw_engine, name="Zatwierdzający Odchodzący")
    await grant(rw_engine, world.a, leaving, Role.APPROVER)
    change = await ready_change(api, world, change_type="emergency", approver_id=str(leaving.id))
    assert (await action(api, world, change["id"], "implement", world.editor)).status_code == 200
    url = changes_url(world.a.id, UUID(change["id"]))
    card = (await api.get(url, headers=auth(world.approver))).json()
    assert card["editable_fields"] == []  # the designated approver can still approve
    await grant(rw_engine, world.a, leaving)  # all roles revoked
    card = (await api.get(url, headers=auth(world.approver))).json()
    assert card["editable_fields"] == ["approver_id"]
    version = card["version"]
    by_editor = await api.patch(
        url,
        json={"approver_id": str(world.editor.id), "version": version},
        headers=auth(world.editor),
    )
    assert_problem(by_editor, 409, "change.frozen")  # the assignee never re-points
    moved = await api.patch(
        url,
        json={"approver_id": str(world.approver.id), "version": version},
        headers=auth(world.approver),
    )
    assert moved.status_code == 200, moved.text
    entry = (await audit_entries(rw_engine, UUID(change["id"])))[-1]
    assert (entry.action, set(entry.diff)) == ("update", {"approver_id"})
    approved = await action(api, world, change["id"], "approve", world.approver)
    assert approved.status_code == 200, approved.text
    assert approved.json()["change"]["approved_by"]["id"] == str(world.approver.id)


async def test_attachment_downloads_are_audited(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    change = await ready_change(api, world)
    url = changes_url(world.a.id, UUID(change["id"]), "/attachments")
    upload = await api.post(
        url, files={"file": ("log.txt", b"dziennik", "text/plain")}, headers=auth(world.editor)
    )
    attachment = upload.json()
    for who in (world.viewer, world.auditor):
        assert (await api.get(f"{url}/{attachment['id']}", headers=auth(who))).status_code == 200
    entries = await audit_entries(rw_engine, UUID(attachment["id"]))
    assert [(e.action, e.actor_id) for e in entries] == [
        ("attach", world.editor.id),
        ("download", world.viewer.id),
        ("download", world.auditor.id),
    ]
    assert {e.company_id for e in entries} == {world.a.id}
    assert entries[1].context["sha256"] == attachment["sha256"]
    assert entries[1].context["filename"] == "log.txt"
    # a missing attachment is not recorded
    await api.get(f"{url}/{uuid4()}", headers=auth(world.viewer))
    assert len(await audit_entries(rw_engine, UUID(attachment["id"]))) == 3
    assert (await verify(rw_engine, world.a.id)).ok


async def test_chain_status_badge(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    from app.services import audit as audit_service
    from tests.test_audit_verify import tamper_entry

    company = await make_company(rw_engine)
    await grant(rw_engine, company, world.viewer, Role.VIEWER)
    await grant(rw_engine, company, world.auditor, Role.AUDITOR)
    await grant(rw_engine, company, world.editor, Role.EDITOR)
    url = f"/api/v1/companies/{company.id}/audit/status"
    never = (await api.get(url, headers=auth(world.viewer))).json()
    assert (never["status"], never["ok"], never["checked_at"]) == ("unknown", None, None)

    verify_url = "/api/v1/audit/verify"
    params = {"company_id": str(company.id)}
    verified = await api.post(verify_url, params=params, headers=auth(world.auditor))
    assert verified.json()["ok"] is True
    await make_change(rw_engine, company, world.editor, Role.EDITOR)  # entries after it
    fresh = (await api.get(url, headers=auth(world.viewer))).json()
    assert (fresh["status"], fresh["ok"]) == ("ok", True)
    assert fresh["checked_at"].endswith("Z")
    assert fresh["head_seq"] > fresh["verified_head_seq"]
    assert set(fresh) == {"status", "ok", "checked_at", "verified_head_seq", "head_seq"}

    async with scoped(rw_engine, [company.id]) as session:
        later = await audit_service.chain_status(
            session,
            company.id,
            max_age=timedelta(hours=26),
            now=datetime.now(UTC) + timedelta(hours=27),
        )
    assert later.status == "stale"

    # an entry appended after the verification is forged: broken, without details
    await tamper_entry(owner_engine, company.id, fresh["head_seq"])
    broken = (await api.get(url, headers=auth(world.viewer))).json()
    assert (broken["status"], broken["ok"]) == ("broken", False)
    # ... and a failed verification is reported as broken as well
    await api.post(verify_url, params=params, headers=auth(world.auditor))
    assert (await api.get(url, headers=auth(world.viewer))).json()["status"] == "broken"


# --------------------------------------------------------------------------- re-review fixes


async def test_chain_status_ignores_entries_appended_after_its_head(
    world: World, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deterministic race: an entry is COMMITTED by another transaction right after the
    status read the chain head (READ COMMITTED: later statements see it). The verdict is
    judged as of that head - ``ok``, not a false ``broken``."""
    from app.domain.audit import Actor
    from app.services import audit as audit_service

    company = await make_company(rw_engine)
    async with scoped(rw_engine, [company.id]) as session:
        await audit_service.verify_and_record(session, company.id, actor=Actor.system())
    await make_change(rw_engine, company, world.editor, Role.EDITOR)

    original = audit_service._read_head

    async def read_head_then_concurrent_write(session: Any, company_id: Any) -> Any:
        head = await original(session, company_id)
        await make_change(rw_engine, company, world.editor, Role.EDITOR)  # other session
        return head

    monkeypatch.setattr(audit_service, "_read_head", read_head_then_concurrent_write)
    async with scoped(rw_engine, [company.id]) as session:
        status = await audit_service.chain_status(
            session, company.id, max_age=timedelta(hours=26), now=datetime.now(UTC)
        )
    monkeypatch.setattr(audit_service, "_read_head", original)
    assert status.status == "ok"
    # The entry written meanwhile is beyond the judged head ...
    async with scoped(rw_engine, [company.id]) as session:
        current = await audit_service.chain_status(
            session, company.id, max_age=timedelta(hours=26), now=datetime.now(UTC)
        )
    assert current.head_seq > status.head_seq
    assert current.status == "ok"  # ... and is checked by the next request (new head)


async def test_chain_status_is_stale_beyond_the_tail_limit(
    world: World, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-request cost is bounded: too many entries since the last verification ->
    ``stale`` (no claim), never a silent ``ok``."""
    from app.domain.audit import Actor
    from app.services import audit as audit_service

    company = await make_company(rw_engine)
    async with scoped(rw_engine, [company.id]) as session:
        await audit_service.verify_and_record(session, company.id, actor=Actor.system())
    for _ in range(3):
        await make_change(rw_engine, company, world.editor, Role.EDITOR)

    async def status() -> str:
        async with scoped(rw_engine, [company.id]) as session:
            result = await audit_service.chain_status(
                session, company.id, max_age=timedelta(hours=26), now=datetime.now(UTC)
            )
        return result.status

    assert await status() == "ok"
    monkeypatch.setattr(audit_service, "STATUS_TAIL_LIMIT", 2)
    assert await status() == "stale"


async def test_owner_lock_only_for_changes_needing_the_consent(
    api: AsyncClient, available: World, rw_engine: AsyncEngine
) -> None:
    world = available
    ci = await make_ci(rw_engine, world.a, world.ci_type, owner_user_id=world.viewer.id)
    change = await ready_change(api, world, ci_ids=[ci.id])
    await action(api, world, change["id"], "submit", world.editor)  # pending, no consent rule
    moved = await api.patch(
        f"/api/v1/companies/{world.a.id}/ci/{ci.id}",
        json={"owner_user_id": str(world.editor.id)},
        headers=auth(world.editor),
    )
    assert moved.status_code == 200, moved.text


async def test_consent_by_the_requester_is_marked(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    ot = await make_category(rw_engine, requires_ci_owner_consent=True, default_risk="high")
    await make_available(rw_engine, world.a, ot)
    own = await make_ci(rw_engine, world.a, world.ci_type, owner_user_id=world.editor.id)
    other = await make_ci(rw_engine, world.a, world.ci_type, owner_user_id=world.viewer.id)
    change = await ready_change(api, world, category_id=str(ot.id), ci_ids=[own.id, other.id])
    await action(api, world, change["id"], "submit", world.editor)
    await action(api, world, change["id"], "consent", world.editor)
    done = await action(api, world, change["id"], "consent", world.viewer)
    consents = {c["ci_id"]: c for c in done.json()["change"]["consents"]}
    assert consents[str(own.id)]["by_requester_or_assignee"] is True
    assert consents[str(other.id)]["by_requester_or_assignee"] is False
    assert all(c["valid"] for c in consents.values())


async def test_register_filter_by_who_approved(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    standard = await make_category(rw_engine, requires_approval=False)
    await make_available(rw_engine, world.a, standard, world.category)
    auto = await ready_change(
        api, world, category_id=str(standard.id), change_type="standard", risk="low"
    )
    await action(api, world, auto["id"], "submit", world.editor)
    manual = await ready_change(api, world)
    await action(api, world, manual["id"], "submit", world.editor)
    await action(api, world, manual["id"], "approve", world.approver)
    await ready_change(api, world)  # not approved

    async def numbers(**params: Any) -> set[str]:
        response = await api.get(changes_url(world.a.id), params=params, headers=auth(world.viewer))
        assert response.status_code == 200, response.text
        return {i["number"] for i in response.json()["items"]}

    assert await numbers(approved_by="system") == {auto["number"]}
    assert await numbers(approved_by=str(world.approver.id)) == {manual["number"]}
    # the designated approver of both is the approver
    assert await numbers(approver=str(world.approver.id)) >= {auto["number"], manual["number"]}
    bad = await api.get(
        changes_url(world.a.id), params={"approved_by": "nikt"}, headers=auth(world.viewer)
    )
    assert_problem(bad, 422, "change.invalid_filter")
