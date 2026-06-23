"""Knowledge base schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    config: dict = {}


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    config: dict | None = None


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    document_count: int
    created_at: datetime
