"""Chat session / message schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Sessions ───────────────────────────────────────────────────
class SessionCreate(BaseModel):
    title: str | None = None
    category: str | None = None
    knowledge_base_id: uuid.UUID | None = None
    metadata: dict = {}


class SessionUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    pinned: bool | None = None
    status: str | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    knowledge_base_id: uuid.UUID | None
    title: str
    category: str | None
    status: str
    pinned: bool
    message_count: int
    created_at: datetime
    updated_at: datetime


# ── Citations / messages ───────────────────────────────────────
class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: uuid.UUID | None
    chunk_id: uuid.UUID | None
    document_name: str | None
    chunk_reference: str | None
    page_number: int | None
    confidence: float | None
    source_link: str | None
    snippet: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    reaction: str | None
    is_edited: bool
    model: str | None
    provider: str | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int | None
    citations: list[CitationOut] = []
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: uuid.UUID | None = None
    knowledge_base_id: uuid.UUID | None = None
    use_rag: bool = True
    use_tools: bool = True
    stream: bool = True


class RegenerateRequest(BaseModel):
    message_id: uuid.UUID


class EditMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ReactionRequest(BaseModel):
    reaction: str | None  # null clears it
