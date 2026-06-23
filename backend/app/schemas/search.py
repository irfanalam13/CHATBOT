"""Search schemas — semantic / hybrid / keyword / metadata / global."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    knowledge_base_id: uuid.UUID | None = None
    mode: Literal["semantic", "keyword", "hybrid", "metadata"] = "hybrid"
    top_k: int = Field(8, ge=1, le=50)
    rerank: bool = True
    filters: dict = {}


class SearchHit(BaseModel):
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID | None
    document_name: str | None
    content: str
    score: float
    page_number: int | None = None
    metadata: dict = {}


class SearchResponse(BaseModel):
    query: str
    mode: str
    hits: list[SearchHit]
    took_ms: int


class GlobalSearchResponse(BaseModel):
    query: str
    documents: list[SearchHit]
    chats: list[dict]
    took_ms: int
