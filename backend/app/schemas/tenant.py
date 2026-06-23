"""Tenant + settings schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    description: str | None
    created_at: datetime


class TenantUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class TenantSettingsUpdate(BaseModel):
    llm_provider: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    system_prompt: str | None = None
    chunk_strategy: str | None = None
    chunk_size: int | None = Field(None, ge=100, le=4000)
    chunk_overlap: int | None = Field(None, ge=0, le=1000)
    retrieval_top_k: int | None = Field(None, ge=1, le=50)
    enable_reranking: bool | None = None
    enable_tools: bool | None = None
    # Plaintext keys; encrypted before persistence.
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    extra: dict | None = None


class TenantSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    llm_provider: str | None
    llm_model: str | None
    embedding_provider: str | None
    embedding_model: str | None
    system_prompt: str | None
    chunk_strategy: str | None
    chunk_size: int | None
    chunk_overlap: int | None
    retrieval_top_k: int | None
    enable_reranking: bool
    enable_tools: bool
    # Keys never returned — only whether they are set.
    has_anthropic_key: bool = False
    has_openai_key: bool = False
    has_google_key: bool = False
