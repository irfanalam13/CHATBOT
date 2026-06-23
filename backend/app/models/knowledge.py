"""Knowledge bases — logical groupings of documents within a tenant."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_kb_tenant_slug"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Overrides for embedding/chunking at KB granularity.
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    document_count: Mapped[int] = mapped_column(default=0)
