"""Queue of background report jobs (arq + Redis; CLAUDE.md §9, ADR 0017 §8).

The API enqueues ``generate_report`` (``app.worker``) while the request transaction is
still open; the job id is derived from the report id (enqueued once). The worker retries
until the row is committed and visible. A queue that cannot be reached fails the request
(503 ``report.queue_unavailable``) - the transaction rolls back, so no ``pending`` row is
left without a job.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from app.errors import ProblemError

logger = logging.getLogger(__name__)

JOB_NAME = "generate_report"


def queue_unavailable() -> ProblemError:
    return ProblemError(
        status=503,
        code="report.queue_unavailable",
        detail="Kolejka generowania raportów jest chwilowo niedostępna. Spróbuj ponownie "
        "za chwilę lub zawęź raport.",
    )


class ReportQueue(Protocol):
    async def enqueue(self, job: dict[str, Any]) -> None: ...

    async def aclose(self) -> None: ...


class ArqReportQueue:
    """Lazily connected arq pool (no Redis connection until the first large report)."""

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url
        self._pool: Any = None

    async def _get_pool(self) -> Any:
        if self._pool is None:
            from arq import create_pool
            from arq.connections import RedisSettings

            self._pool = await create_pool(RedisSettings.from_dsn(self._redis_url))
        return self._pool

    async def enqueue(self, job: dict[str, Any]) -> None:
        try:
            pool = await self._get_pool()
            await pool.enqueue_job(JOB_NAME, job, _job_id=f"report:{job['report_id']}")
        except ProblemError:
            raise
        except Exception as exc:
            logger.error("report job could not be enqueued: %s", type(exc).__name__)
            raise queue_unavailable() from exc

    async def aclose(self) -> None:
        if self._pool is not None:
            await self._pool.aclose()
            self._pool = None
