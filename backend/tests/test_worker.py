from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.db import Database
from app.worker import (
    WorkerSettings,
    auth_maintenance,
    ping,
    report_maintenance,
    shutdown,
    startup,
    verify_audit_chains,
)


def cron_of(coroutine: object) -> Any:
    (job,) = [j for j in WorkerSettings.cron_jobs if j.coroutine is coroutine]
    return job


async def test_ping_task() -> None:
    assert await ping({}) == "pong"


def test_worker_settings_registers_ping_and_redis() -> None:
    assert ping in WorkerSettings.functions
    assert WorkerSettings.redis_settings.host


def test_auth_maintenance_runs_every_minute_once_per_cluster() -> None:
    """ADR 0010 §4: closed login_failed windows are summarized within about a minute."""
    job = cron_of(auth_maintenance)
    assert job.second == 0
    assert job.minute is None
    assert job.unique  # one run per tick even with several workers
    assert auth_maintenance in WorkerSettings.functions


async def test_startup_and_shutdown_manage_the_database() -> None:
    ctx: dict[str, object] = {}
    await startup(ctx)
    assert isinstance(ctx["db"], Database)
    await shutdown(ctx)
    await shutdown({})  # nothing to close


def test_audit_chains_are_verified_daily() -> None:
    """ADR 0013 §11: keeps the "Łańcuch spójny" badge fresh (max age 26 h by default)."""
    job = cron_of(verify_audit_chains)
    assert (job.hour, job.minute, job.second) == (2, 30, 0)
    assert job.unique
    assert verify_audit_chains in WorkerSettings.functions


def test_report_maintenance_runs_every_five_minutes() -> None:
    """ADR 0017 §14: stale ``pending`` reports are failed, orphaned files removed."""
    job = cron_of(report_maintenance)
    assert job.minute == set(range(0, 60, 5))
    assert job.unique
    assert report_maintenance in WorkerSettings.functions


@pytest.mark.db
async def test_verify_all_chains_records_every_verification(rw_engine: AsyncEngine) -> None:
    from app.services.audit_schedule import verify_all_chains
    from tests.factories import make_company, scoped

    company = await make_company(rw_engine)
    report = await verify_all_chains(async_sessionmaker(rw_engine, expire_on_commit=False))
    assert report.verified >= 2  # every company + the global chain
    # other tests tamper with their own chains on purpose; this company is intact
    assert str(company.id) not in report.broken
    async with scoped(rw_engine, [company.id]) as session:
        from datetime import timedelta

        from app.services import audit
        from app.services.changes import db_now

        status = await audit.chain_status(
            session, company.id, max_age=timedelta(hours=26), now=await db_now(session)
        )
    assert status.status == "ok"
