"""Analytics events + token usage / cost ledger."""
from __future__ import annotations

import uuid

from sqlalchemy import Float, Index, Integer, String
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    # Dashboard aggregates filter by tenant_id + created_at, often + event_type.
    __table_args__ = (
        Index(
            "ix_analytics_tenant_type_created",
            "tenant_id", "event_type", "created_at",
        ),
        Index("ix_analytics_tenant_created", "tenant_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    # question_asked, search_failed, topic, feedback, knowledge_used, login ...
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)


class TokenUsage(Base):
    """Per-message token + cost ledger for billing and cost tracking."""

    __tablename__ = "token_usage"
    # Cost/usage rollups filter by tenant_id + created_at.
    __table_args__ = (
        Index("ix_token_usage_tenant_created", "tenant_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    operation: Mapped[str] = mapped_column(String(50), default="chat")  # chat | embedding | rerank
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
