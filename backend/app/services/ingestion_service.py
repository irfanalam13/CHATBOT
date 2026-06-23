"""Document processing pipeline:
upload → validate → (virus) scan → extract → clean → chunk → embed → index →
store chunk metadata → version. Runs inside a Celery worker via asyncio.run.
"""
from __future__ import annotations

import hashlib
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.core.security import decrypt_value
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentVersion,
)
from app.models.knowledge import KnowledgeBase
from app.rag.chunking import chunk_text
from app.rag.embeddings import get_embedder
from app.rag.extractors import extract
from app.rag.vectorstore import get_vector_store, new_point_id
from app.repositories.repos import get_tenant_settings
from app.security.guards import detect_rag_poisoning, sanitize_retrieved
from app.services.storage import get_storage

log = get_logger("services.ingestion")


def _clean(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _virus_scan(data: bytes) -> bool:
    """Placeholder hook. Wire ClamAV / S3 malware scanning here.

    Returns True when the file is clean. The EICAR test signature is rejected.
    """
    return b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" not in data


async def process_document(document_id: str) -> None:
    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, uuid.UUID(document_id))
        if not doc:
            log.warning("document_missing", document_id=document_id)
            return
        try:
            await _run_pipeline(session, doc)
            await session.commit()
        except Exception as e:
            log.exception("ingestion_failed", document_id=document_id)
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)[:2000]
            await session.commit()


async def _run_pipeline(session: AsyncSession, doc: Document) -> None:
    from app.models.tenant import Tenant

    storage = get_storage()
    ts = await get_tenant_settings(session, doc.tenant_id)
    kb = await session.get(KnowledgeBase, doc.knowledge_base_id)
    tenant = await session.get(Tenant, doc.tenant_id)
    collection = tenant.vector_collection

    # 1. Validate + scan
    doc.status = DocumentStatus.SCANNING
    await session.flush()
    data = storage.get(doc.storage_key)
    if not _virus_scan(data):
        raise ValueError("File failed virus scan")

    # 2. Extract + clean
    doc.status = DocumentStatus.EXTRACTING
    await session.flush()
    raw_text, page_map = extract(doc.filename, data)
    text = _clean(raw_text)
    if not text:
        raise ValueError("No extractable text found")

    # 3. Chunk
    doc.status = DocumentStatus.CHUNKING
    await session.flush()
    strategy = (kb.config or {}).get("chunk_strategy") or (ts.chunk_strategy if ts else None)
    size = (ts.chunk_size if ts and ts.chunk_size else settings.CHUNK_SIZE)
    overlap = (ts.chunk_overlap if ts and ts.chunk_overlap is not None else settings.CHUNK_OVERLAP)
    chunks = chunk_text(text, strategy=strategy, size=size, overlap=overlap, page_map=page_map)

    # 4. Embed + index
    doc.status = DocumentStatus.EMBEDDING
    await session.flush()
    api_keys = _tenant_embedding_keys(ts)
    embedder = get_embedder(
        ts.embedding_provider if ts else None,
        ts.embedding_model if ts else None,
        api_keys=api_keys,
    )
    store = get_vector_store()
    await store.ensure_collection(collection, embedder.dimension)

    texts = [c.content for c in chunks]
    vectors = await embedder.embed(texts)

    points: list[dict] = []
    indexed = 0
    for chunk, vector in zip(chunks, vectors):
        # RAG-poisoning guard + dedup.
        if not detect_rag_poisoning(chunk.content).allowed:
            chunk.content = sanitize_retrieved(chunk.content)
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()
        if await store.content_hash_exists(collection, str(doc.tenant_id), content_hash):
            continue

        chunk_id = uuid.uuid4()
        point_id = new_point_id()
        session.add(
            DocumentChunk(
                id=chunk_id,
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                vector_id=uuid.UUID(point_id),
                chunk_index=chunk.index,
                content=chunk.content,
                content_hash=content_hash,
                page_number=chunk.page_number,
                token_count=len(chunk.content) // 4,
                metadata_={"level": chunk.metadata.get("level", "chunk")},
            )
        )
        points.append(
            {
                "id": point_id,
                "vector": vector,
                "payload": {
                    "tenant_id": str(doc.tenant_id),
                    "knowledge_base_id": str(doc.knowledge_base_id),
                    "document_id": str(doc.id),
                    "document_name": doc.filename,
                    "chunk_id": str(chunk_id),
                    "content": chunk.content,
                    "content_hash": content_hash,
                    "page_number": chunk.page_number,
                    "source_link": doc.source_url,
                    "metadata": chunk.metadata,
                },
            }
        )
        indexed += 1

    doc.status = DocumentStatus.INDEXING
    await session.flush()
    if points:
        await store.upsert(collection, points)

    # 5. Version + finalize
    doc.chunk_count = indexed
    doc.status = DocumentStatus.READY
    session.add(
        DocumentVersion(
            tenant_id=doc.tenant_id,
            document_id=doc.id,
            version=doc.version,
            storage_key=doc.storage_key,
            checksum=doc.checksum,
            chunk_count=indexed,
        )
    )
    if kb:
        kb.document_count = (kb.document_count or 0) + (1 if doc.version == 1 else 0)
    log.info("ingestion_complete", document_id=str(doc.id), chunks=indexed)


def _tenant_embedding_keys(ts) -> dict[str, str]:
    keys: dict[str, str] = {}
    if ts and ts.openai_api_key_enc:
        keys["openai"] = decrypt_value(ts.openai_api_key_enc)
    if ts and ts.google_api_key_enc:
        keys["google"] = decrypt_value(ts.google_api_key_enc)
    return keys
