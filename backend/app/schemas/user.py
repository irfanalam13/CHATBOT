"""User schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LooseEmail


class UserCreate(BaseModel):
    email: LooseEmail
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    role: str = "employee"
    custom_permissions: list[str] = []


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    custom_permissions: list[str] | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    email: LooseEmail
    full_name: str | None
    role: str
    custom_permissions: list[str]
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
