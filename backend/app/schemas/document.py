"""Document schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    file_type: str | None
    content_type: str | None
    size_bytes: int
    status: str
    version: int
    chunk_count: int
    error_message: str | None
    created_at: datetime


class DocumentChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None
    token_count: int | None


class IngestUrlRequest(BaseModel):
    url: str
    knowledge_base_id: uuid.UUID


class IngestTextRequest(BaseModel):
    knowledge_base_id: uuid.UUID
    filename: str
    text: str
