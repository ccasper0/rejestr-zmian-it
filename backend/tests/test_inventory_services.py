"""Services of the dictionaries and the CI inventory: races and edge cases (ADR 0011).

The races are deterministic: transaction 1 writes and keeps its transaction open, so
transaction 2 passes the application pre-check (it cannot see the uncommitted change),
blocks on a lock (unique index, company row, parent category) and - once transaction 1
commits - must turn the conflict into 409/422, never a 500. Its audit entry must not
survive (rolled back with the business row).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.db import apply_company_scope
from app.errors import ProblemError
from app.services import categories, ci_types, companies, configuration_items
from tests.factories import (
    SYSTEM,
    World,
    audit_entries,
    make_category,
    make_ci,
    make_company,
    random_category_code,
    random_ci_type_code,
    scoped,
    verify,
)

pytestmark = pytest.mark.db


Operation = Callable[[AsyncSession], Awaitable[Any]]


async def _overlap(
    engine: AsyncEngine,
    scope: list[Any],
    operation: Operation,
    second_operation: Operation | None = None,
) -> asyncio.Task[Any]:
    """Transaction 1 runs ``operation`` and stays open; transaction 2 runs
    ``second_operation`` (default: the same) and must block. Transaction 1 then commits;
    the finished (or failed) task of transaction 2 is returned."""
    first = AsyncSession(engine, expire_on_commit=False)
    await first.begin()
    await apply_company_scope(first, scope, admin_scope=True)
    await operation(first)

    async def second() -> Any:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            await session.execute(text("SET LOCAL lock_timeout = '10s'"))
            await apply_company_scope(session, scope, admin_scope=True)
            return await (second_operation or operation)(session)

    task = asyncio.create_task(second())
    await asyncio.sleep(0.5)  # let transaction 2 block on transaction 1's lock
    assert not task.done(), "transaction 2 was not serialized behind transaction 1"
    await first.commit()
    await first.close()
    await asyncio.wait([task])
    return task


async def _race(
    engine: AsyncEngine,
    scope: list[Any],
    operation: Operation,
    second_operation: Operation | None = None,
) -> ProblemError:
    """Like ``_overlap``; transaction 2 must fail with a problem - returned."""
    task = await _overlap(engine, scope, operation, second_operation)
    with pytest.raises(ProblemError) as info:
        task.result()
    return info.value


async def test_concurrent_ci_identifier_is_409(rw_engine: AsyncEngine, world: World) -> None:
    async def create(session: AsyncSession) -> Any:
        return await configuration_items.create_item(
            session,
            actor=SYSTEM,
            company=world.a,
            ci_type_id=world.ci_type.id,
            identifier="RACE-CI-01",
            name="Wyścig",
        )

    error = await _race(rw_engine, [world.a.id], create)
    assert (error.status, error.code) == (409, "ci.identifier_taken")
    assert (await verify(rw_engine, world.a.id)).ok


async def test_concurrent_ci_type_code_is_409(rw_engine: AsyncEngine, world: World) -> None:
    code = random_ci_type_code()

    async def create(session: AsyncSession) -> Any:
        return await ci_types.create_ci_type(session, actor=SYSTEM, code=code, name="Wyścig")

    error = await _race(rw_engine, [], create)
    assert (error.status, error.code) == (409, "ci_type.code_taken")
    assert (await verify(rw_engine, None)).ok


async def test_concurrent_category_code_is_409(rw_engine: AsyncEngine, world: World) -> None:
    code = random_category_code()

    async def create(session: AsyncSession) -> Any:
        return await categories.create_category(session, actor=SYSTEM, code=code, name="Wyścig")

    error = await _race(rw_engine, [], create)
    assert (error.status, error.code) == (409, "category.code_taken")


async def test_unknown_fields_are_a_programming_error(rw_engine: AsyncEngine, world: World) -> None:
    async with scoped(rw_engine, [world.a.id], admin_scope=True) as session:
        for call in (
            categories.update_category(
                session, actor=SYSTEM, category_id=world.category.id, changes={"x": 1}
            ),
            ci_types.update_ci_type(
                session, actor=SYSTEM, ci_type_id=world.ci_type.id, changes={"x": 1}
            ),
            configuration_items.update_item(
                session, actor=SYSTEM, company=world.a, ci_id=world.ci_a.id, changes={"x": 1}
            ),
        ):
            with pytest.raises(ValueError, match="not updatable"):
                await call


@pytest.mark.parametrize("target", ["category", "ci_type", "ci"])
async def test_blank_names_are_rejected_on_update(
    rw_engine: AsyncEngine, world: World, target: str
) -> None:
    async with scoped(rw_engine, [world.a.id], admin_scope=True) as session:
        if target == "category":
            call = categories.update_category(
                session, actor=SYSTEM, category_id=world.category.id, changes={"name": " "}
            )
        elif target == "ci_type":
            call = ci_types.update_ci_type(
                session, actor=SYSTEM, ci_type_id=world.ci_type.id, changes={"name": " "}
            )
        else:
            call = configuration_items.update_item(
                session,
                actor=SYSTEM,
                company=world.a,
                ci_id=world.ci_a.id,
                changes={"identifier": " "},
            )
        with pytest.raises(ProblemError) as info:
            await call
    assert (info.value.status, info.value.code) == (422, f"{target}.invalid_data")


async def test_unchanged_updates_write_nothing(rw_engine: AsyncEngine, world: World) -> None:
    from tests.factories import audit_entries

    before = {
        key: len(await audit_entries(rw_engine, entity))
        for key, entity in (("t", world.ci_type.id), ("c", world.category.id))
    }
    async with scoped(rw_engine, admin_scope=True) as session:
        await ci_types.update_ci_type(
            session,
            actor=SYSTEM,
            ci_type_id=world.ci_type.id,
            changes={"name": world.ci_type.name, "code": world.ci_type.code, "is_active": True},
        )
        changed = await categories.update_category(
            session,
            actor=SYSTEM,
            category_id=world.category.id,
            changes={"requires_approval": False},
        )
    assert changed.requires_approval is False
    after = {
        key: len(await audit_entries(rw_engine, entity))
        for key, entity in (("t", world.ci_type.id), ("c", world.category.id))
    }
    assert after == {"t": before["t"], "c": before["c"] + 1}


async def test_top_level_listing(rw_engine: AsyncEngine, world: World) -> None:
    child = await make_category(rw_engine, parent=world.category)
    async with scoped(rw_engine) as session:
        roots, _ = await categories.list_categories(session, roots_only=True, limit=500, offset=0)
        found = await categories.get_category(session, child.id)
    codes = {c.code for c in roots}
    assert world.category.code in codes
    assert child.code not in codes
    assert found is not None
    assert found.parent_id == world.category.id


async def test_concurrent_ci_identifier_change_is_409(rw_engine: AsyncEngine, world: World) -> None:
    """PATCH: two CI renamed concurrently to the same identifier (ignoring case)."""
    second_ci = await make_ci(rw_engine, world.a, world.ci_type)

    def rename(ci_id: Any, identifier: str) -> Operation:
        async def run(session: AsyncSession) -> Any:
            return await configuration_items.update_item(
                session,
                actor=SYSTEM,
                company=world.a,
                ci_id=ci_id,
                changes={"identifier": identifier},
            )

        return run

    error = await _race(
        rw_engine,
        [world.a.id],
        rename(world.ci_a.id, "RACE-PATCH-01"),
        rename(second_ci.id, "race-patch-01"),
    )
    assert (error.status, error.code) == (409, "ci.identifier_taken")
    assert [e.action for e in await audit_entries(rw_engine, second_ci.id)] == ["create"]
    assert (await verify(rw_engine, world.a.id)).ok


async def test_ci_write_racing_an_archive_is_rejected(rw_engine: AsyncEngine, world: World) -> None:
    """Archive first (company row FOR UPDATE, uncommitted): the CI write passes the
    service check on its stale company object, then the trigger (FOR SHARE) waits and
    sees the archived company - 409, no CI, no audit entry."""
    company = await make_company(rw_engine)
    ci = await make_ci(rw_engine, company, world.ci_type)
    assert company.status == "active"

    async def archive(session: AsyncSession) -> Any:
        return await companies.archive_company(session, actor=SYSTEM, company_id=company.id)

    async def create(session: AsyncSession) -> Any:
        return await configuration_items.create_item(
            session,
            actor=SYSTEM,
            company=company,  # loaded before the archive: the service check passes
            ci_type_id=world.ci_type.id,
            identifier="RACE-ARCH-01",
            name="Wyścig z archiwizacją",
        )

    async def update(session: AsyncSession) -> Any:
        return await configuration_items.update_item(
            session, actor=SYSTEM, company=company, ci_id=ci.id, changes={"name": "Po archiwum"}
        )

    for writer in (create, update):
        if writer is update:
            # Reopen for the second round (the first round archived the company).
            async with scoped(rw_engine, [company.id], admin_scope=True) as session:
                await session.execute(
                    text("UPDATE companies SET status = 'active' WHERE id = :c"), {"c": company.id}
                )
        error = await _race(rw_engine, [company.id], archive, writer)
        assert (error.status, error.code) == (409, "company.archived")

    async with scoped(rw_engine, [company.id]) as session:
        rows, total = await configuration_items.list_items(session, company.id, limit=10, offset=0)
    assert [r.item.name for r in rows] == ["Obiekt testowy"]
    assert total == 1
    assert [e.action for e in await audit_entries(rw_engine, ci.id)] == ["create"]
    assert (await verify(rw_engine, company.id)).ok


async def test_archive_waits_for_a_ci_write_in_progress(
    rw_engine: AsyncEngine, world: World
) -> None:
    """CI write first (company row FOR SHARE): the archive waits for it, then succeeds -
    the CI was created while the company was active."""
    company = await make_company(rw_engine)

    async def create(session: AsyncSession) -> Any:
        return await configuration_items.create_item(
            session,
            actor=SYSTEM,
            company=company,
            ci_type_id=world.ci_type.id,
            identifier="BEFORE-ARCH-01",
            name="Przed archiwizacją",
        )

    async def archive(session: AsyncSession) -> Any:
        return await companies.archive_company(session, actor=SYSTEM, company_id=company.id)

    task = await _overlap(rw_engine, [company.id], create, archive)
    assert task.result().status == "archived"
    async with scoped(rw_engine, [company.id]) as session:
        _, total = await configuration_items.list_items(session, company.id, limit=10, offset=0)
    assert total == 1


async def test_subcategory_racing_parent_deactivation_is_rejected(
    rw_engine: AsyncEngine, world: World
) -> None:
    parent = await make_category(rw_engine)

    async def deactivate(session: AsyncSession) -> Any:
        return await categories.update_category(
            session, actor=SYSTEM, category_id=parent.id, changes={"is_active": False}
        )

    async def create_child(session: AsyncSession) -> Any:
        return await categories.create_category(
            session,
            actor=SYSTEM,
            code=random_category_code(),
            name="Podkategoria w wyścigu",
            parent_id=parent.id,
        )

    error = await _race(rw_engine, [], deactivate, create_child)
    assert (error.status, error.code) == (422, "category.parent_inactive")
    async with scoped(rw_engine) as session:
        children, total = await categories.list_categories(
            session, parent_id=parent.id, limit=10, offset=0
        )
    assert (children, total) == ([], 0)
