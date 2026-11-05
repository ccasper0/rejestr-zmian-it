"""SQLAlchemy models. Import every model module here so Alembic sees all tables."""

from app.models.audit import AuditChainHead, AuditLog
from app.models.auth import (
    AuthFailureWindow,
    AuthLogin,
    AuthRefreshToken,
    AuthSession,
    UserCredential,
)
from app.models.base import Base
from app.models.changes import (
    Attachment,
    Change,
    ChangeCiConsent,
    ChangeComment,
    ChangeItem,
    NumberSequence,
)
from app.models.identity import Company, CompanyMembership, User
from app.models.inventory import ChangeCategory, CiType, CompanyCategory, ConfigurationItem
from app.models.reports import ReportExport, ReportNumberSequence

__all__ = [
    "Attachment",
    "AuditChainHead",
    "AuditLog",
    "AuthFailureWindow",
    "AuthLogin",
    "AuthRefreshToken",
    "AuthSession",
    "Base",
    "Change",
    "ChangeCategory",
    "ChangeCiConsent",
    "ChangeComment",
    "ChangeItem",
    "CiType",
    "Company",
    "CompanyCategory",
    "CompanyMembership",
    "ConfigurationItem",
    "NumberSequence",
    "ReportExport",
    "ReportNumberSequence",
    "User",
    "UserCredential",
]
