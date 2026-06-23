"""Documents, their processing lifecycle, versions and chunk records."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from app.core.db_types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    SCANNING = "scanning"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    file_type: Mapped[str | None] = mapped_column(String(32))   # pdf, docx, ...
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)

    storage_key: Mapped[str | None] = mapped_column(String(1024))  # S3 object key
    source_url: Mapped[str | None] = mapped_column(String(1024))

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADED, nullable=False, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """Chunk metadata mirror of what lives in Qdrant (source of truth for citations)."""

    __tablename__ = "document_chunks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # The point id used in the Qdrant collection.
    vector_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # parent/child
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)  # dedup
    page_number: Mapped[int | None] = mapped_column(Integer)
    token_count: Mapped[int | None] = mapped_column(Integer)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class DocumentVersion(Base):
    """Immutable snapshot of a document each time it is re-ingested."""

    __tablename__ = "document_versions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    checksum: Mapped[str | None] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
