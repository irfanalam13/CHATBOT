"""Chat sessions, messages, citations and layered conversation memory."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Index, Integer, String, Text
from app.core.db_types import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MemoryScope(str, enum.Enum):
    SESSION = "session"
    USER = "user"
    TENANT = "tenant"


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    # The session list endpoint filters tenant_id + user_id + status together.
    __table_args__ = (
        Index("ix_chat_sessions_tenant_user_status", "tenant_id", "user_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    title: Mapped[str] = mapped_column(String(512), default="New chat")
    category: Mapped[str | None] = mapped_column(String(120), index=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False, index=True
    )
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    # Rolling running summary used for context-window optimisation.
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    # Every history/transcript read orders a session's messages by time.
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    # For regenerate / edit chains.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    reaction: Mapped[str | None] = mapped_column(String(32))  # 👍 / 👎 / emoji

    # Telemetry.
    model: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str | None] = mapped_column(String(50))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    finish_reason: Mapped[str | None] = mapped_column(String(50))
    tool_calls: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
    citations: Mapped[list["MessageCitation"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageCitation(Base):
    __tablename__ = "message_citations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_name: Mapped[str | None] = mapped_column(String(512))
    chunk_reference: Mapped[str | None] = mapped_column(String(255))
    page_number: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_link: Mapped[str | None] = mapped_column(String(1024))
    snippet: Mapped[str | None] = mapped_column(Text)

    message: Mapped["Message"] = relationship(back_populates="citations")


class Memory(Base):
    """Long-term memory items at session / user / tenant scope."""

    __tablename__ = "memories"
    # Relevance lookup filters by tenant_id + scope + owner_id together.
    __table_args__ = (
        Index("ix_memories_tenant_scope_owner", "tenant_id", "scope", "owner_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scope: Mapped[MemoryScope] = mapped_column(Enum(MemoryScope), nullable=False, index=True)
    # Owner reference: session_id for SESSION scope, user_id for USER scope, null for TENANT.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    key: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
