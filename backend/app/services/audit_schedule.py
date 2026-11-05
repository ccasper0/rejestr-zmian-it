"""Scheduled verification of every audit chain (worker cron, ADR 0013 §11).

Keeps the "Łańcuch spójny" badge of the change card (``GET /companies/{id}/audit/status``)
fresh: each company chain, then the global chain, is verified and the verification is
recorded (``audit.verify_and_record``, actor ``system``, ``context.source = "worker"``).
One short transaction per chain with exactly that chain in scope (ADR 0009 §4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db import apply_company_scope
from app.domain.audit import Actor
from app.models import Company
from app.services import audit

CONTEXT = {"source": "worker", "job": "verify_audit_chains"}


@dataclass
class ScheduleReport:
    verified: int = 0
    broken: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"verified": self.verified, "broken": list(self.broken)}


async def verify_all_chains(sessionmaker: async_sessionmaker[AsyncSession]) -> ScheduleReport:
    report = ScheduleReport()
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, [], admin_scope=True)
        company_ids: list[UUID] = list(
            (await session.execute(select(Company.id).order_by(Company.id))).scalars()
        )
    for company_id in company_ids:
        async with sessionmaker() as session, session.begin():
            await apply_company_scope(session, [company_id])
            outcome = await audit.verify_and_record(
                session, company_id, actor=Actor.system(), context=CONTEXT
            )
        report.verified += 1
        if not outcome.verification.result.ok:
            report.broken.append(str(company_id))
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, [], global_audit_read=True)
        outcome = await audit.verify_and_record(
            session, None, actor=Actor.system(), context=CONTEXT
        )
    report.verified += 1
    if not outcome.verification.result.ok:
        report.broken.append("global")
    return report
