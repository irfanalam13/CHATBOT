"""Per-tenant tool definitions for function calling (CRM/ERP/HR/etc.)."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, String, Text, UniqueConstraint
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ToolCategory(str, enum.Enum):
    CRM = "crm"
    ERP = "erp"
    ACCOUNTING = "accounting"
    INVENTORY = "inventory"
    HR = "hr"
    MEDICAL = "medical"
    CUSTOM = "custom"


class ToolDefinition(Base):
    __tablename__ = "tool_definitions"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_tool_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[ToolCategory] = mapped_column(
        Enum(ToolCategory), default=ToolCategory.CUSTOM, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON Schema for the tool's input (Anthropic / OpenAI compatible).
    input_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    # How to execute: http webhook config { url, method, headers, auth } or "builtin".
    handler_type: Mapped[str] = mapped_column(String(50), default="http")
    handler_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
