"""Company isolation at the API level (CLAUDE.md §7.3), driven by ``tests/isolation_cases.py``.

- member endpoints: a user without membership in the company gets 404, byte-for-byte the
  same problem as for a non-existent company (apart from ``instance`` / ``request_id``);
- admin-only endpoints: non-admins get the same 403 for their own, a foreign and a
  non-existent company;
- denied requests have no side effects on the target company (data, roles, audit chain);
- the app admin without membership: only declared admin paths work.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.main import create_app
from app.permissions import route_declarations
from tests.conftest import make_settings
from tests.factories import World, add_changes, add_report, auth, scoped
from tests.isolation_cases import (
    ADMIN_CASES,
    CASES,
    MEMBER_CASES,
    QUERY_CASES,
    REPORT_BODY_ROUTES,
    REPORT_RESOURCE_ROUTES,
    RESOURCE_CASES,
    IsolationCase,
    QueryIsolationCase,
)
from tests.test_api_auth import assert_problem

A_MEMBERS = ("approver", "editor", "auditor", "viewer")
NON_ADMINS = (*A_MEMBERS, "outsider", "nobody")
VOLATILE = {"instance", "request_id"}


@pytest.fixture
async def world(world: World, rw_engine: AsyncEngine) -> World:
    """The shared world plus changes of A and B (resources of the stage 4 routes)."""
    return await add_report(rw_engine, await add_changes(rw_engine, world))


def _ids(cases: tuple[IsolationCase, ...]) -> list[Any]:
    return [pytest.param(c, id=c.key) for c in cases]


def stable(response: Response) -> dict[str, Any]:
    body: dict[str, Any] = response.json()
    return {k: v for k, v in body.items() if k not in VOLATILE}


async def call(
    api: AsyncClient, case: IsolationCase, world: World, persona: str, cid: UUID
) -> Response:
    return await api.request(
        case.method,
        case.url(world, cid),
        **case.send(world),
        headers=auth(world.persona(persona)),
    )


async def company_state(engine: AsyncEngine, company_id: UUID) -> tuple[Any, ...]:
    """Everything a denied request could have changed in the company."""
    async with scoped(engine, [company_id], admin_scope=True) as session:
        company = (
            await session.execute(
                text(
                    "SELECT name, prefix, status, tax_id, is_ksc_entity, default_approver_id, "
                    "updated_at FROM companies WHERE id = :c"
                ),
                {"c": company_id},
            )
        ).one()
        roles = (
            await session.execute(
                text(
                    "SELECT user_id, role FROM company_memberships WHERE company_id = :c "
                    "ORDER BY user_id, role"
                ),
                {"c": company_id},
            )
        ).all()
        chain = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": company_id}
            )
        ).scalar_one()
    return (tuple(company), tuple(map(tuple, roles)), chain)


# --------------------------------------------------------------------------- coverage


def test_cases_cover_every_company_scoped_route() -> None:
    app = create_app(make_settings())
    routes = {
        f"{method} {route.path}"
        for route in route_declarations(app)
        for method in route.methods
        if "{company_id}" in route.path
    }
    keys = [c.key for c in CASES]
    assert len(keys) == len(set(keys)), "duplicate isolation case"
    assert routes - set(keys) == set(), "add these routes to tests/isolation_cases.py"
    assert set(keys) - routes == set(), "stale isolation cases"
    # Kinds agree with the declarations in app.permissions (single source of truth).
    declared = {f"{m} {r.path}": r.rules for r in route_declarations(app) for m in r.methods}
    for case in CASES:
        (rule,) = declared[case.key]
        if case.access == "admin":
            assert rule.kind == "admin_company", case.key
        else:
            assert rule.kind == "company", case.key
            assert (rule.admin_action is not None) == case.admin_path, case.key


# --------------------------------------------------------------------------- member endpoints


@pytest.mark.db
@pytest.mark.parametrize("case", _ids(MEMBER_CASES))
async def test_foreign_company_is_404_like_a_missing_one(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, case: IsolationCase
) -> None:
    pairs = [
        *((p, world.b.id) for p in A_MEMBERS),
        ("outsider", world.a.id),
        ("nobody", world.a.id),
        ("nobody", world.b.id),
    ]
    for persona, target in pairs:
        before = await company_state(rw_engine, target)
        foreign = await call(api, case, world, persona, target)
        missing = await call(api, case, world, persona, uuid4())
        assert_problem(foreign, 404, "company.not_found")
        assert_problem(missing, 404, "company.not_found")
        assert stable(foreign) == stable(missing), (persona, case.key)
        assert await company_state(rw_engine, target) == before, (persona, case.key)
    # Sanity: the endpoint works for members of the company (the 404 is about the company).
    for persona in case.ok_personas:
        own = await call(api, case, world, persona, world.a.id)
        assert own.status_code < 400, (persona, case.key, own.text)


@pytest.mark.db
@pytest.mark.parametrize("case", _ids(MEMBER_CASES))
async def test_admin_without_membership_only_on_declared_admin_path(
    api: AsyncClient, world: World, case: IsolationCase
) -> None:
    foreign = await call(api, case, world, "admin", world.b.id)
    missing = await call(api, case, world, "admin", uuid4())
    if case.admin_path:
        assert foreign.status_code < 400, foreign.text
    else:
        assert_problem(foreign, 404, "company.not_found")
        assert stable(foreign) == stable(missing)
    assert_problem(missing, 404, "company.not_found")


@pytest.mark.db
@pytest.mark.parametrize("case", _ids(RESOURCE_CASES))
async def test_foreign_resource_under_own_company_path_is_404(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, case: IsolationCase
) -> None:
    """A resource of company B under company A's path: 404 for every member of A who may
    use the endpoint at all (others get the resource-independent 403 first), and for the
    app admin on the admin path of A - identical to a resource that does not exist.
    Nothing changes in B."""
    assert case.foreign_resource is not None
    params = await case.foreign_resource(rw_engine, world, world.b)
    before = await company_state(rw_engine, world.b.id)
    for persona in (*case.ok_personas, *(("admin",) if case.admin_path else ())):
        foreign = await api.request(
            case.method,
            case.url(world, world.a.id, **params),
            **case.send(world),
            headers=auth(world.persona(persona)),
        )
        missing = await api.request(
            case.method,
            case.url(world, world.a.id, **{k: case.missing_value(k) for k in params}),
            **case.send(world),
            headers=auth(world.persona(persona)),
        )
        assert foreign.status_code == 404, (persona, case.key, foreign.text)
        assert stable(foreign) == stable(missing), (persona, case.key)
    assert await company_state(rw_engine, world.b.id) == before


# --------------------------------------------------------------------------- admin endpoints


@pytest.mark.db
@pytest.mark.parametrize("case", _ids(ADMIN_CASES))
async def test_admin_only_endpoints_do_not_reveal_existence(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, case: IsolationCase
) -> None:
    before = {cid: await company_state(rw_engine, cid) for cid in (world.a.id, world.b.id)}
    for persona in NON_ADMINS:
        answers = [
            await call(api, case, world, persona, cid) for cid in (world.a.id, world.b.id, uuid4())
        ]
        for response in answers:
            assert_problem(response, 403, "auth.forbidden")
        assert len({repr(stable(r)) for r in answers}) == 1, (persona, case.key)
    assert {cid: await company_state(rw_engine, cid) for cid in before} == before

    missing = await call(api, case, world, "admin", uuid4())
    assert_problem(missing, 404, "company.not_found")


# --------------------------------------------------------------------------- company in the query


def _query_params(dependant: Any) -> set[str]:
    """Query parameter names of a route, including those of its dependencies."""
    names: set[str] = set()
    stack = [dependant]
    while stack:
        current = stack.pop()
        names |= {q.alias or q.name for q in current.query_params}
        stack.extend(current.dependencies)
    return names


def _query_company_routes() -> set[str]:
    from fastapi.routing import APIRoute, iter_route_contexts

    app = create_app(make_settings())
    found = set()
    for context in iter_route_contexts(app.routes):
        if not isinstance(context.original_route, APIRoute):
            continue
        if "company_id" in _query_params(context.dependant):
            found |= {f"{m} {context.path}" for m in context.methods or ()}
    assert found, "the introspection found nothing - check the FastAPI internals it uses"
    return found


def test_query_cases_cover_every_route_with_a_company_query_parameter() -> None:
    keys = [c.key for c in QUERY_CASES]
    assert len(keys) == len(set(keys)), "duplicate isolation case"
    assert _query_company_routes() == set(keys), "update QUERY_CASES in tests/isolation_cases.py"


def _query_ids(cases: tuple[QueryIsolationCase, ...]) -> list[Any]:
    return [pytest.param(c, id=c.key) for c in cases]


@pytest.mark.db
@pytest.mark.parametrize("case", _query_ids(QUERY_CASES))
async def test_foreign_company_in_query_is_404_like_a_missing_one(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, case: QueryIsolationCase
) -> None:
    async def ask(persona: str, cid: UUID) -> Response:
        return await api.request(
            case.method,
            case.path,
            params={"company_id": str(cid)},
            headers=auth(world.persona(persona)),
        )

    pairs = [
        *((p, world.b.id) for p in A_MEMBERS),
        ("outsider", world.a.id),
        ("nobody", world.a.id),
        ("nobody", world.b.id),
    ]
    for persona, target in pairs:
        before = await company_state(rw_engine, target)
        foreign = await ask(persona, target)
        missing = await ask(persona, uuid4())
        assert_problem(foreign, 404, "company.not_found")
        assert_problem(missing, 404, "company.not_found")
        assert stable(foreign) == stable(missing), (persona, case.key)
        assert await company_state(rw_engine, target) == before, (persona, case.key)
    for persona in case.allowed_personas:
        own = await ask(persona, world.a.id)
        assert own.status_code == 200, (persona, case.key, own.text)
        if case.method == "GET":
            assert {i["company_id"] for i in own.json()["items"]} == {str(world.a.id)}
    admin = await ask("admin", world.b.id)
    if case.admin_path:
        assert admin.status_code == 200, admin.text
    else:
        assert_problem(admin, 404, "company.not_found")
    assert_problem(await ask("admin", uuid4()), 404, "company.not_found")
    if case.path == "/api/v1/reports":
        listed = (await ask("admin", world.b.id)).json()["items"]
        assert {i["company_id"] for i in listed} <= {str(world.b.id)}


# --------------------------------------------------------------------------- reports (ADR 0017)


def test_report_routes_are_the_known_ones() -> None:
    """Every route under /reports is covered by the report isolation tests below."""
    app = create_app(make_settings())
    routes = {r.path for r in route_declarations(app) if r.path.startswith("/api/v1/reports")}
    assert routes == {*REPORT_RESOURCE_ROUTES, *REPORT_BODY_ROUTES}


@pytest.mark.db
@pytest.mark.parametrize("path", REPORT_RESOURCE_ROUTES)
async def test_foreign_report_is_404_like_a_missing_one(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, path: str
) -> None:
    from app.permissions import Role
    from tests.factories import make_report

    foreign = await make_report(
        rw_engine, [world.b], world.outsider, {world.b.id: {Role.EDITOR, Role.APPROVER}}
    )
    before = await company_state(rw_engine, world.b.id)
    for persona in (*A_MEMBERS, "nobody"):
        headers = auth(world.persona(persona))
        theirs = await api.get(path.format(report_id=foreign.id), headers=headers)
        missing = await api.get(path.format(report_id=uuid4()), headers=headers)
        assert_problem(theirs, 404, "report.not_found")
        assert stable(theirs) == stable(missing), (persona, path)
    assert await company_state(rw_engine, world.b.id) == before
    # Sanity: the author and the app admin (admin export path) see it.
    for persona in ("outsider", "admin"):
        own = await api.get(path.format(report_id=foreign.id), headers=auth(world.persona(persona)))
        assert own.status_code == 200, (persona, own.text)


@pytest.mark.db
async def test_ordering_a_report_of_a_foreign_company_is_404_like_a_missing_one(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    def body(company_id: UUID, kind: str = "register") -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": kind,
            "company_id": str(company_id),
            "period_from": "2000-01-01T00:00:00Z",
            "period_to": "2100-01-01T00:00:00Z",
        }
        if kind == "change_card":
            assert world.draft_b is not None
            result = {
                "kind": kind,
                "company_id": str(company_id),
                "change_id": str(world.draft_b.id),
            }
        return result

    before = await company_state(rw_engine, world.b.id)
    for persona in (*A_MEMBERS, "nobody"):
        for kind in ("register", "change_card"):
            headers = auth(world.persona(persona))
            foreign = await api.post(
                "/api/v1/reports", json=body(world.b.id, kind), headers=headers
            )
            missing = await api.post("/api/v1/reports", json=body(uuid4(), kind), headers=headers)
            assert_problem(foreign, 404, "company.not_found")
            assert stable(foreign) == stable(missing), (persona, kind)
    assert await company_state(rw_engine, world.b.id) == before
    # A change of B under the path of A: 404 change.not_found (no report row created).
    assert world.draft_b is not None
    swapped = await api.post(
        "/api/v1/reports",
        json={
            "kind": "change_card",
            "company_id": str(world.a.id),
            "change_id": str(world.draft_b.id),
        },
        headers=auth(world.editor),
    )
    assert_problem(swapped, 404, "change.not_found")
