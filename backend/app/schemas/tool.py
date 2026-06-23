"""Tool definition schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9_-]+$")
    category: str = "custom"
    description: str
    input_schema: dict
    handler_type: str = "http"
    handler_config: dict = {}


class ToolUpdate(BaseModel):
    description: str | None = None
    input_schema: dict | None = None
    handler_config: dict | None = None
    is_active: bool | None = None


class ToolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str
    description: str
    input_schema: dict
    handler_type: str
    is_active: bool
    created_at: datetime
