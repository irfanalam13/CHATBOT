"""Retrieval pipeline: query → embed → search → rerank → context + citations."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.core.config import settings
from app.rag.embeddings import get_embedder
from app.rag.reranker import rerank
from app.rag.vectorstore import VectorHit, get_vector_store


@dataclass
class RetrievedChunk:
    chunk_id: str | None
    document_id: str | None
    document_name: str | None
    content: str
    score: float
    page_number: int | None
    source_link: str | None
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    chunks: list[RetrievedChunk]
    took_ms: int

    def to_context(self, max_chars: int = 12000) -> str:
        """Build the grounding context block with inline citation markers."""
        lines, total = [], 0
        for i, c in enumerate(self.chunks, start=1):
            ref = c.document_name or "source"
            page = f", p.{c.page_number}" if c.page_number else ""
            block = f"[{i}] (Source: {ref}{page})\n{c.content}\n"
            if total + len(block) > max_chars:
                break
            lines.append(block)
            total += len(block)
        return "\n".join(lines)


class Retriever:
    def __init__(self, embedding_provider=None, embedding_model=None, api_keys=None):
        self._embedder = get_embedder(embedding_provider, embedding_model, api_keys=api_keys)
        self._store = get_vector_store()

    async def retrieve(
        self,
        *,
        collection: str,
        tenant_id: str,
        query: str,
        mode: str = "hybrid",
        top_k: int | None = None,
        rerank_enabled: bool | None = None,
        filters: dict | None = None,
    ) -> RetrievalResult:
        start = time.perf_counter()
        top_k = top_k or settings.RETRIEVAL_TOP_K
        rerank_enabled = (
            settings.ENABLE_RERANKING if rerank_enabled is None else rerank_enabled
        )

        if mode == "keyword":
            hits = await self._store.keyword_search(
                collection, query, tenant_id=tenant_id, top_k=top_k, filters=filters
            )
        else:
            qvec = await self._embedder.embed_one(query)
            if mode == "hybrid":
                hits = await self._store.hybrid_search(
                    collection, qvec, query, tenant_id=tenant_id, top_k=top_k, filters=filters
                )
            else:  # semantic / metadata
                hits = await self._store.search(
                    collection, qvec, tenant_id=tenant_id, top_k=top_k, filters=filters
                )

        if rerank_enabled and hits:
            hits = rerank(query, hits, settings.RERANK_TOP_N)

        chunks = [self._to_chunk(h) for h in hits]
        took = int((time.perf_counter() - start) * 1000)
        return RetrievalResult(chunks=chunks, took_ms=took)

    @staticmethod
    def _to_chunk(hit: VectorHit) -> RetrievedChunk:
        p = hit.payload
        return RetrievedChunk(
            chunk_id=p.get("chunk_id"),
            document_id=p.get("document_id"),
            document_name=p.get("document_name"),
            content=p.get("content", ""),
            score=hit.score,
            page_number=p.get("page_number"),
            source_link=p.get("source_link"),
            metadata=p.get("metadata", {}),
        )
