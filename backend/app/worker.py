"""Background worker (arq): ``arq app.worker.WorkerSettings``.

- ``auth_maintenance`` (cron, every minute): writes the exact totals of closed
  ``login_failed`` aggregation windows to the audit log and purges operational
  authentication state that is no longer needed (ADR 0010 §3-4);
- ``verify_audit_chains`` (cron, daily 02:30 UTC): verifies and records every audit
  chain, so the "Łańcuch spójny" badge of the change card stays fresh (ADR 0013 §11);
- ``generate_report`` (enqueued by ``POST /reports``): large register reports in the
  background (CLAUDE.md §9, ADR 0017 §8); its own ``timeout`` / ``max_tries``;
- ``report_maintenance`` (cron, every 5 minutes): reports ``pending`` for longer than the
  job timeout + margin -> ``failed``, report files without a ``done`` row removed
  (ADR 0017 §14).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, ClassVar
from uuid import UUID

from arq import Retry, cron
from arq.connections import RedisSettings
from arq.worker import func

from app.config import get_settings
from app.db import Database
from app.logs import configure_logging
from app.reports.render import weasyprint_pdf
from app.services import audit_schedule, auth_events, report_jobs

logger = logging.getLogger(__name__)

# The job is enqueued before the request transaction commits: retry until the row is
# visible (or give up - the request was rolled back and the row never existed).
REPORT_ROW_RETRIES = 10
REPORT_ROW_RETRY_SECONDS = 2
# A report of thousands of changes with the audit trails may take minutes.
REPORT_JOB_TIMEOUT_SECONDS = 900
# A report still pending after the job timeout, the row-visibility retries and this
# margin has no live job: the maintenance cron fails it (ADR 0017 §14).
REPORT_STALE_MARGIN_SECONDS = 300
REPORT_STALE_AFTER = timedelta(
    seconds=REPORT_JOB_TIMEOUT_SECONDS
    + REPORT_ROW_RETRIES * REPORT_ROW_RETRY_SECONDS
    + REPORT_STALE_MARGIN_SECONDS
)


async def ping(ctx: dict[str, Any]) -> str:
    """Smoke-test task."""
    return "pong"


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    # After arq's own logging.config.dictConfig: the worker logs like the API (JSON lines,
    # secrets masked, ADR 0019 §4).
    configure_logging(settings.log_level, settings.log_format)
    ctx["db"] = Database.from_settings(settings)


async def shutdown(ctx: dict[str, Any]) -> None:
    db: Database | None = ctx.get("db")
    if db is not None:
        await db.dispose()


async def auth_maintenance(ctx: dict[str, Any]) -> dict[str, int]:
    """Flush closed failure windows into the audit log, then purge expired state.

    Short transactions per batch (``auth_events.maintenance``), each with an EMPTY company
    scope: only global audit entries can be written (RLS); the auth state tables have no
    company data.
    """
    db: Database = ctx["db"]
    report = await auth_events.maintenance(db.sessionmaker)
    return dict(report.as_dict())


async def verify_audit_chains(ctx: dict[str, Any]) -> dict[str, object]:
    db: Database = ctx["db"]
    report = await audit_schedule.verify_all_chains(db.sessionmaker)
    return report.as_dict()


async def generate_report(ctx: dict[str, Any], job: dict[str, Any]) -> str:
    """Generate a ``pending`` report (``app.services.report_jobs.run``).

    The transaction runs as the user who ordered the report (``app.user_id``) with the
    companies of the report as its RLS scope; the permission is checked again."""
    db: Database = ctx["db"]
    settings = get_settings()
    outcome = await report_jobs.run(
        db.sessionmaker,
        report_id=UUID(str(job["report_id"])),
        user_id=UUID(str(job["user_id"])),
        company_ids=[UUID(str(c)) for c in job["company_ids"]],
        renderer=ctx.get("pdf_renderer", weasyprint_pdf),
        storage_root=settings.storage_path,
        max_changes=settings.report_max_changes,
        admin_path=bool(job.get("admin_path", False)),
    )
    if outcome == "not_visible":
        if int(ctx.get("job_try", 1)) < REPORT_ROW_RETRIES:
            raise Retry(defer=REPORT_ROW_RETRY_SECONDS)
        logger.warning("report %s never became visible; job dropped", job["report_id"])
    return outcome


async def report_maintenance(ctx: dict[str, Any]) -> dict[str, int]:
    """Fail reports left ``pending`` (lost job, crashed worker) and remove report files
    without a ``done`` row (``app.services.report_jobs.maintenance``)."""
    db: Database = ctx["db"]
    report = await report_jobs.maintenance(
        db.sessionmaker,
        storage_root=get_settings().storage_path,
        stale_after=REPORT_STALE_AFTER,
    )
    return report.as_dict()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [
        ping,
        auth_maintenance,
        verify_audit_chains,
        report_maintenance,
        # Only the report job gets the long timeout and the retries (the row may not be
        # committed yet when the job starts); the other functions keep arq's defaults.
        func(
            generate_report,
            timeout=REPORT_JOB_TIMEOUT_SECONDS,
            max_tries=REPORT_ROW_RETRIES,
        ),
    ]
    cron_jobs: ClassVar[list[Any]] = [
        cron(auth_maintenance, second=0, run_at_startup=True),
        # Verifying every chain may take minutes (it had the former global job_timeout).
        cron(verify_audit_chains, hour=2, minute=30, second=0, timeout=900),
        cron(report_maintenance, minute=set(range(0, 60, 5)), second=30, run_at_startup=True),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings: ClassVar[RedisSettings] = RedisSettings.from_dsn(get_settings().redis_url)
