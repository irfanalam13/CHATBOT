"""Tenant + per-tenant settings. The root of the multi-tenancy tree."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


class Tenant(Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus), default=TenantStatus.TRIAL, nullable=False
    )
    # Logical name of the Qdrant collection owned by this tenant.
    vector_collection: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    settings: Mapped["TenantSettings"] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )

    # LLM configuration (overrides platform defaults).
    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    embedding_provider: Mapped[str | None] = mapped_column(String(50))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    system_prompt: Mapped[str | None] = mapped_column(Text)

    # Encrypted per-tenant provider keys (nullable → fall back to platform key).
    anthropic_api_key_enc: Mapped[str | None] = mapped_column(Text)
    openai_api_key_enc: Mapped[str | None] = mapped_column(Text)
    google_api_key_enc: Mapped[str | None] = mapped_column(Text)

    # RAG knobs.
    chunk_strategy: Mapped[str | None] = mapped_column(String(50))
    chunk_size: Mapped[int | None] = mapped_column()
    chunk_overlap: Mapped[int | None] = mapped_column()
    retrieval_top_k: Mapped[int | None] = mapped_column()
    enable_reranking: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_tools: Mapped[bool] = mapped_column(Boolean, default=True)

    # Free-form extra config.
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    tenant: Mapped["Tenant"] = relationship(back_populates="settings")
