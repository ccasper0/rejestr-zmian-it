"""Request/response schemas: change categories, CI types, company categories, CI."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import SafeLine, SafeStr, UtcDateTime

RiskValue = Literal["low", "medium", "high"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- categories


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    parent_id: UUID | None
    requires_approval: bool
    requires_ci_owner_consent: bool
    default_risk: RiskValue
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CategoryCreate(_Strict):
    code: SafeLine = Field(max_length=50, description="Np. NET lub NET-VLAN; niezmienny")
    name: SafeLine = Field(max_length=500)
    parent_id: UUID | None = Field(default=None, description="Kategoria główna (podkategoria)")
    requires_approval: bool | None = Field(
        default=None, description="Brak: jak kategoria nadrzędna, a dla kategorii głównej: tak"
    )
    default_risk: RiskValue | None = None
    requires_ci_owner_consent: bool = Field(
        default=False, description="Zgoda właściciela obiektu (CI) przed zatwierdzeniem (OT)"
    )


class CategoryUpdate(_Strict):
    """Only provided fields change. ``code`` and ``parent_id`` only unchanged (immutable)."""

    code: SafeLine | None = Field(default=None, max_length=50)
    name: SafeLine | None = Field(default=None, max_length=500)
    parent_id: UUID | None = None
    requires_approval: bool | None = None
    requires_ci_owner_consent: bool | None = None
    default_risk: RiskValue | None = None
    is_active: bool | None = None


# --------------------------------------------------------------------------- CI types


class CiTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CiTypeCreate(_Strict):
    code: SafeLine = Field(max_length=50, description="Np. network_device; niezmienny")
    name: SafeLine = Field(max_length=500)


class CiTypeUpdate(_Strict):
    code: SafeLine | None = Field(default=None, max_length=50)
    name: SafeLine | None = Field(default=None, max_length=500)
    is_active: bool | None = None


# --------------------------------------------------------------------------- company categories


class CompanyCategoryOut(BaseModel):
    category_id: UUID
    code: str
    name: str
    requires_approval: bool
    default_risk: RiskValue
    is_active: bool
    approver_override_id: UUID | None


class CompanyCategoriesOut(BaseModel):
    items: list[CompanyCategoryOut]


class CompanyCategoryIn(_Strict):
    category_id: UUID
    approver_override_id: UUID | None = None


class CompanyCategoriesIn(_Strict):
    """The FULL list of categories available in the company (missing = withdrawn)."""

    categories: list[CompanyCategoryIn] = Field(max_length=500)


# --------------------------------------------------------------------------- CI


class CiOut(BaseModel):
    id: UUID
    company_id: UUID
    ci_type_id: UUID
    ci_type_code: str
    ci_type_name: str
    identifier: str
    name: str
    description: str | None
    owner_user_id: UUID | None
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CiCreate(_Strict):
    ci_type_id: UUID
    identifier: SafeLine = Field(max_length=500, description="Np. FW-01; unikalny w spółce")
    name: SafeLine = Field(max_length=500)
    description: SafeStr | None = Field(default=None, max_length=10_000)
    owner_user_id: UUID | None = None


class CiUpdate(_Strict):
    """Only provided fields change; ``is_active = false`` deactivates (no deletion)."""

    ci_type_id: UUID | None = None
    identifier: SafeLine | None = Field(default=None, max_length=500)
    name: SafeLine | None = Field(default=None, max_length=500)
    description: SafeStr | None = Field(default=None, max_length=10_000)
    owner_user_id: UUID | None = None
    is_active: bool | None = None
