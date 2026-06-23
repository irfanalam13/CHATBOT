"""Auth request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import LooseEmail


class RegisterTenantRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    admin_email: LooseEmail
    admin_password: str = Field(min_length=8, max_length=128)
    admin_full_name: str | None = None


class LoginRequest(BaseModel):
    email: LooseEmail
    password: str
    tenant_slug: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    scopes: list[str] = []
