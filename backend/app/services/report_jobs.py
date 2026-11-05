"""Background generation of a report (``app.worker.generate_report``; ADR 0017 §8, §14).

One transaction as the user who ordered the report: ``app.user_id`` = that user (the RLS
of multi-company rows), company scope = the companies of the report (nothing else is
visible or writable), the row locked ``FOR UPDATE`` (one worker generates it). The
permission is checked AGAIN - a user who lost the role since ordering gets a failed
report, not the data. The data is read in a separate REPEATABLE READ READ ONLY snapshot
(one consistent view of the changes, the trails and the chain verification); the row and
the audit entries are written in the READ COMMITTED transaction (an audit head locked
``FOR UPDATE`` under REPEATABLE READ would fail on every concurrent append).

A failed generation is recorded (status ``failed`` + audit entry) in the same transaction
after rolling back to a savepoint. A job cancelled (``job_timeout``, worker shutdown) or
failing outside that savepoint (e.g. at COMMIT) is recorded as ``failed`` in a NEW
transaction before the error propagates; whatever still escapes (a lost job, a crashed
worker) is failed later by :func:`fail_stale` (the worker's maintenance cron).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import apply_company_scope, set_current_user, snapshot_session
from app.domain.reports import ReportKind, ReportStatus
from app.domain.roles import Role
from app.errors import ProblemError
from app.models import ReportExport
from app.reports.render import PdfRenderer
from app.services import memberships, reports, users

logger = logging.getLogger(__name__)

Outcome = Literal["done", "failed", "skipped", "not_visible"]

GENERIC_ERROR = reports.GENERIC_ERROR
NO_PERMISSION = "Zlecający nie ma już uprawnień do eksportu danych tego raportu."
TIMEOUT_ERROR = "Przekroczono czas generowania raportu. Zawęź raport lub spróbuj ponownie."
INACTIVE_USER = "(użytkownik nieaktywny)"

# Bound of the clean-up after a cancellation (the task is already being cancelled).
CLEANUP_TIMEOUT_SECONDS = 30

_KIND_ROLES: dict[str, frozenset[str]] = {
    # Mirrors app.permissions.PERMISSIONS (export.register / export.change_card) for the
    # membership roles; tests/test_reports.py checks the two agree.
    ReportKind.REGISTER.value: frozenset({Role.APPROVER.value, Role.AUDITOR.value}),
    ReportKind.CHANGE_CARD.value: frozenset(
        {Role.APPROVER.value, Role.EDITOR.value, Role.AUDITOR.value}
    ),
}


def still_allowed(report: ReportExport, exporter: reports.Exporter) -> bool:
    """The rule of ``app.permissions.require_report_order`` evaluated now."""
    if report.company_id is None:
        return all(
            Role.AUDITOR.value in exporter.roles_by_company.get(cid, frozenset())
            for cid in report.scope_company_ids
        )
    if exporter.is_app_admin:
        return True
    roles = exporter.roles_by_company.get(report.company_id, frozenset())
    return bool(roles & _KIND_ROLES[report.kind])


async def _exporter(session: AsyncSession, user_id: UUID) -> reports.Exporter | None:
    user = await users.get_user(session, user_id)
    if user is None or not user.is_active:
        return None
    roles = await memberships.roles_by_company(session, user_id)
    return reports.Exporter(
        user_id=user.id,
        display_name=user.display_name,
        roles_by_company={cid: frozenset(r.value for r in rs) for cid, rs in roles.items()},
        is_app_admin=user.is_app_admin,
    )


async def _actor(session: AsyncSession, user_id: UUID) -> reports.Exporter:
    """The ordering user as the audit actor of a failure (also when no longer active)."""
    return await _exporter(session, user_id) or reports.Exporter(user_id, INACTIVE_USER, {})


async def _begin_as(session: AsyncSession, user_id: UUID, company_ids: Sequence[UUID]) -> None:
    await set_current_user(session, user_id)
    await apply_company_scope(session, company_ids)


async def _generate(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    report_id: UUID,
    user_id: UUID,
    company_ids: Sequence[UUID],
    renderer: PdfRenderer,
    storage_root: Path,
    max_changes: int,
    extra: Mapping[str, object],
) -> Outcome:
    async with sessionmaker() as session, session.begin():
        await _begin_as(session, user_id, company_ids)
        report = await reports.lock_pending(session, report_id)
        if report is None:
            return "not_visible"
        if report.status != ReportStatus.PENDING.value:
            return "skipped"  # already generated (a repeated job)
        exporter = await _exporter(session, user_id)
        if exporter is None or report.generated_by_id != user_id:
            logger.warning("report %s: the ordering user is not active", report.number)
            exporter = exporter or reports.Exporter(user_id, INACTIVE_USER, {})
            await reports.fail(session, report, exporter=exporter, error=NO_PERMISSION, extra=extra)
            return "failed"
        if set(report.scope_company_ids) != set(company_ids) or not still_allowed(report, exporter):
            await reports.fail(session, report, exporter=exporter, error=NO_PERMISSION, extra=extra)
            return "failed"
        try:
            async with (
                session.begin_nested(),
                snapshot_session(
                    sessionmaker, company_ids=company_ids, user_id=user_id
                ) as data_session,
            ):
                await reports.generate(
                    session,
                    report,
                    exporter=exporter,
                    renderer=renderer,
                    storage_root=storage_root,
                    max_changes=max_changes,
                    extra=extra,
                    data_session=data_session,
                )
            return "done"
        except ProblemError as exc:
            error = exc.detail
        except Exception:
            logger.exception("report %s could not be generated", report.number)
            error = GENERIC_ERROR
        await session.refresh(report)
        await reports.fail(session, report, exporter=exporter, error=error, extra=extra)
        return "failed"


async def fail_pending(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    report_id: UUID,
    user_id: UUID,
    company_ids: Sequence[UUID],
    error: str,
    extra: Mapping[str, object],
    stale_before: timedelta | None = None,
) -> bool:
    """Mark a report still ``pending`` as ``failed`` (audited) in a NEW transaction as the
    user who ordered it (the RLS of the row and of the company chains). A row locked by a
    running generation is skipped (``SKIP LOCKED``); ``stale_before``: only a row created
    longer ago than that. Returns whether the row was failed."""
    async with sessionmaker() as session, session.begin():
        await _begin_as(session, user_id, company_ids)
        query = (
            select(ReportExport)
            .where(
                ReportExport.id == report_id,
                ReportExport.status == ReportStatus.PENDING.value,
            )
            .with_for_update(skip_locked=True)
        )
        if stale_before is not None:
            query = query.where(ReportExport.created_at < func.now() - stale_before)
        report = (await session.execute(query)).scalar_one_or_none()
        if report is None:
            return False
        exporter = await _actor(session, user_id)
        await reports.fail(session, report, exporter=exporter, error=error, extra=extra)
        return True


async def run(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    report_id: UUID,
    user_id: UUID,
    company_ids: Sequence[UUID],
    renderer: PdfRenderer,
    storage_root: Path,
    max_changes: int,
    admin_path: bool = False,
) -> Outcome:
    """Generate one ``pending`` report (see the module docstring).

    Never leaves the row ``pending`` on a failure it can observe: a cancellation
    (``job_timeout``, shutdown) or an error outside the generation savepoint (e.g. COMMIT)
    fails the row in a NEW transaction, then the error propagates (arq records the job as
    failed)."""
    extra: dict[str, object] = {"source": "worker"}
    if admin_path:
        extra["admin_path"] = True
    try:
        return await _generate(
            sessionmaker,
            report_id=report_id,
            user_id=user_id,
            company_ids=company_ids,
            renderer=renderer,
            storage_root=storage_root,
            max_changes=max_changes,
            extra=extra,
        )
    except (asyncio.CancelledError, TimeoutError) as exc:
        logger.error("report %s: generation cancelled (%s)", report_id, type(exc).__name__)
        await _fail_after(sessionmaker, report_id, user_id, company_ids, TIMEOUT_ERROR, extra)
        raise
    except Exception:
        logger.exception("report %s: generation failed outside its transaction", report_id)
        await _fail_after(sessionmaker, report_id, user_id, company_ids, GENERIC_ERROR, extra)
        raise


async def _fail_after(
    sessionmaker: async_sessionmaker[AsyncSession],
    report_id: UUID,
    user_id: UUID,
    company_ids: Sequence[UUID],
    error: str,
    extra: Mapping[str, object],
) -> None:
    """Best effort (bounded): what is not recorded here is failed by :func:`fail_stale`."""
    try:
        async with asyncio.timeout(CLEANUP_TIMEOUT_SECONDS):
            await fail_pending(
                sessionmaker,
                report_id=report_id,
                user_id=user_id,
                company_ids=company_ids,
                error=error,
                extra=extra,
            )
    except Exception:
        logger.exception("report %s: the failure could not be recorded", report_id)


# --------------------------------------------------------------------------- maintenance


@dataclass(frozen=True, slots=True)
class MaintenanceReport:
    stale_failed: int
    orphans_removed: int

    def as_dict(self) -> dict[str, int]:
        return {"stale_failed": self.stale_failed, "orphans_removed": self.orphans_removed}


async def _admin_read(
    sessionmaker: async_sessionmaker[AsyncSession], statement: str, **params: object
) -> list[Any]:
    """One READ ONLY query on the explicit admin read path (``admin_scope``: RLS lets it
    read every ``report_exports`` row, never write)."""
    async with sessionmaker() as session:
        try:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await apply_company_scope(session, [], admin_scope=True)
            return list((await session.execute(text(statement), params)).all())
        finally:
            await session.rollback()


async def fail_stale(
    sessionmaker: async_sessionmaker[AsyncSession], *, stale_after: timedelta
) -> int:
    """Every report ``pending`` for longer than ``stale_after`` (its job was lost, the
    worker crashed, the clean-up of :func:`run` failed) -> ``failed`` ("Przekroczono czas
    generowania") with the ``failed`` audit entry, each in its own transaction as the
    ordering user."""
    rows = await _admin_read(
        sessionmaker,
        "SELECT id, generated_by_id, scope_company_ids FROM report_exports "
        "WHERE status = 'pending' AND created_at < now() - make_interval(secs => :stale) "
        "ORDER BY created_at",
        stale=stale_after.total_seconds(),
    )
    failed = 0
    for report_id, user_id, company_ids in rows:
        try:
            if await fail_pending(
                sessionmaker,
                report_id=UUID(str(report_id)),
                user_id=UUID(str(user_id)),
                company_ids=[UUID(str(c)) for c in company_ids],
                error=TIMEOUT_ERROR,
                extra={"source": "maintenance"},
                stale_before=stale_after,
            ):
                failed += 1
        except Exception:
            logger.exception("stale report %s could not be failed", report_id)
    return failed


async def remove_orphan_files(
    sessionmaker: async_sessionmaker[AsyncSession], *, storage_root: Path, older_than: timedelta
) -> int:
    """Remove report files with no ``done`` row (a COMMIT that failed after the file was
    written, a crash between the two) and leftover ``.part`` files - only files older than
    ``older_than`` (a generation in progress has not committed yet)."""
    base = reports.resolve(storage_root, "reports")
    if not base.is_dir():
        return 0
    cutoff = time.time() - older_than.total_seconds()

    def candidates() -> list[tuple[Path, str]]:
        found: list[tuple[Path, str]] = []
        for path in base.glob("*/*"):
            if not path.is_file() or path.stat().st_mtime >= cutoff:
                continue
            found.append((path, f"reports/{path.parent.name}/{path.name}"))
        return found

    files = await asyncio.to_thread(candidates)
    if not files:
        return 0
    keys = [key for _, key in files]
    stored = {
        str(r[0])
        for r in await _admin_read(
            sessionmaker,
            "SELECT storage_key FROM report_exports "
            "WHERE status = 'done' AND storage_key = ANY (:keys)",
            keys=keys,
        )
    }
    removed = 0
    for path, key in files:
        if key in stored:
            continue
        logger.warning("removing orphaned report file %s", key)
        await asyncio.to_thread(path.unlink, missing_ok=True)
        removed += 1
    return removed


async def maintenance(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    storage_root: Path,
    stale_after: timedelta,
) -> MaintenanceReport:
    return MaintenanceReport(
        stale_failed=await fail_stale(sessionmaker, stale_after=stale_after),
        orphans_removed=await remove_orphan_files(
            sessionmaker, storage_root=storage_root, older_than=stale_after
        ),
    )
