"""API v1 routers (prefix ``/api/v1`` is added in ``app.main``).

``dev_auth.router`` and ``auth.router`` are NOT part of ``api_router``: ``app.main`` mounts
the first only when ``AUTH_MODE=dev`` and the second only when ``AUTH_MODE=local``.
"""

from fastapi import APIRouter

from app.api.v1 import (
    audit,
    changes,
    companies,
    dictionaries,
    health,
    inventory,
    me,
    permissions,
    reports,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(me.router)
api_router.include_router(companies.router)
api_router.include_router(inventory.router)
# Before changes.router: /changes/export.csv must win over /changes/{change_id}.
api_router.include_router(reports.company_router)
api_router.include_router(changes.router)
api_router.include_router(dictionaries.categories_router)
api_router.include_router(dictionaries.ci_types_router)
api_router.include_router(users.router)
api_router.include_router(permissions.router)
api_router.include_router(audit.router)
api_router.include_router(audit.company_router)
api_router.include_router(reports.router)

__all__ = ["api_router"]
