"""Feedback loop: thumbs, corrections and the human review queue."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FeedbackType(str, enum.Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CORRECTION = "correction"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Feedback(Base):
    __tablename__ = "feedback"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    correction: Mapped[str | None] = mapped_column(Text)  # corrected answer text
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class ReviewQueueItem(Base):
    """Items routed to a human reviewer (low-confidence answers, corrections)."""

    __tablename__ = "review_queue"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
