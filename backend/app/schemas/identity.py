"""Request/response schemas: users, /me, companies, members, local and dev auth."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import SafeLine, UtcDateTime

MembershipRole = Literal["editor", "approver", "auditor", "viewer"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- users


# The login of a local account (ADR 0018): one address, no whitespace, at most 254 chars.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
# Upper bound of a password in a REQUEST (the policy allows 128 code points; a larger
# body is refused before it is hashed).
PASSWORD_INPUT_MAX = 1024

Email = Annotated[SafeLine, Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)]
Password = Annotated[str, Field(min_length=1, max_length=PASSWORD_INPUT_MAX)]


class UserOut(BaseModel):
    """A user for the admin views. Password STATE only - never the hash (ADR 0018)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    email: str
    display_name: str
    is_app_admin: bool
    is_active: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
    # Local account (filled by the API from user_credentials; false/None without one).
    has_password: bool = False
    must_change_password: bool = False
    password_changed_at: UtcDateTime | None = None
    locked_until: UtcDateTime | None = None
    # Deadline of the temporary password (set while must_change_password; in the past =
    # expired, the admin must reset the password). ADR 0018 §12 p. 4.
    temp_password_expires_at: UtcDateTime | None = None


class UserCreate(_Strict):
    email: Email
    display_name: SafeLine = Field(min_length=1, max_length=200)
    is_app_admin: bool = False


class UserUpdate(_Strict):
    """Only provided fields change (the e-mail - the login - is not editable here)."""

    display_name: SafeLine | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    is_app_admin: bool | None = None


class UserWithTemporaryPasswordOut(BaseModel):
    """``POST /users`` and ``POST /users/{id}/reset-password``: the temporary password is
    shown ONCE (it is stored only as an argon2id hash)."""

    user: UserOut
    temporary_password: str


class MembershipOut(BaseModel):
    company_id: UUID
    company_name: str
    company_prefix: str
    company_status: str
    roles: list[str]


class MeOut(BaseModel):
    id: UUID
    external_id: str
    email: str
    display_name: str
    is_app_admin: bool
    # True: only GET /me, POST /auth/password and POST /auth/logout are allowed until the
    # temporary password is changed (403 auth.password_change_required elsewhere).
    must_change_password: bool = False
    memberships: list[MembershipOut]


# --------------------------------------------------------------------------- companies


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tax_id: str | None
    prefix: str
    status: str
    is_ksc_entity: bool
    default_approver_id: UUID | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class CompanyCountsOut(BaseModel):
    """Counters of the admin companies table (§10.4, ADR 0015): CI and members per role."""

    active_ci: int
    all_ci: int
    editors: int
    approvers: int
    auditors: int
    viewers: int


class CompanyListItem(CompanyOut):
    # Roles of the current user in the company (empty for an admin without membership).
    my_roles: list[str]
    counts: CompanyCountsOut


class UserMembershipOut(BaseModel):
    company_id: UUID
    company_name: str
    company_prefix: str
    company_status: str
    roles: list[str]


class UserDetailOut(UserOut):
    """``GET /users/{id}`` (admin): the user with roles in EVERY company (ADR 0015)."""

    memberships: list[UserMembershipOut]


class CompanyCreate(_Strict):
    name: SafeLine = Field(max_length=500)
    prefix: SafeLine = Field(max_length=50, description="Od 2 do 8 wielkich liter A-Z, niezmienny")
    tax_id: SafeLine | None = Field(default=None, max_length=50, description="NIP")
    is_ksc_entity: bool = False
    default_approver_id: UUID | None = None


class CompanyUpdate(_Strict):
    """Only provided fields change. ``prefix`` is accepted only unchanged (immutable)."""

    name: SafeLine | None = Field(default=None, max_length=500)
    prefix: SafeLine | None = Field(default=None, max_length=50)
    tax_id: SafeLine | None = Field(default=None, max_length=50)
    is_ksc_entity: bool | None = None
    default_approver_id: UUID | None = None


# --------------------------------------------------------------------------- members


class MemberOut(BaseModel):
    user_id: UUID
    display_name: str
    email: str
    is_active: bool
    roles: list[str]


class MemberRolesIn(_Strict):
    roles: list[MembershipRole] = Field(max_length=4)


# --------------------------------------------------------------------------- dev auth


class DevUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_id: str
    display_name: str
    email: str
    is_app_admin: bool
    is_active: bool


class DevTokenIn(_Strict):
    external_id: SafeLine = Field(min_length=1, max_length=255)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"  # noqa: S105 - token type, not a secret
    expires_in: int


# --------------------------------------------------------------------------- local auth


class LoginIn(_Strict):
    email: SafeLine = Field(min_length=1, max_length=254)
    password: Password


class RefreshIn(_Strict):
    refresh_token: str = Field(min_length=1, max_length=200)


class PasswordChangeIn(_Strict):
    current_password: Password
    new_password: Password


class SessionTokensOut(TokenOut):
    """``POST /auth/login``, ``/auth/refresh``, ``/auth/password`` (ADR 0018 §4)."""

    refresh_token: str
    refresh_expires_in: int  # seconds until the refresh token expires (idle limit)
    session_expires_at: UtcDateTime  # absolute end of the session (log in again)
    must_change_password: bool
