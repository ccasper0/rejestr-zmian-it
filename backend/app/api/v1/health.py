"""Liveness/readiness probe. Public technical endpoint (see ``permissions.PUBLIC_ENDPOINTS``)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import __version__
from app.db import check_database
from app.errors import PROBLEM_JSON, ProblemError
from app.schemas.health import HealthOut

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthOut,
    responses={503: {"description": "Baza danych niedostępna", "content": {PROBLEM_JSON: {}}}},
)
async def health(db_ok: bool = Depends(check_database)) -> HealthOut:
    if not db_ok:
        raise ProblemError(
            status=503,
            code="health.db_unavailable",
            detail="Baza danych jest niedostępna.",
            extra={"db": "error", "version": __version__},
        )
    return HealthOut(status="ok", version=__version__, db="ok")
