"""Qdrant vector store wrapper — per-tenant collections with metadata filtering,
semantic + keyword + hybrid search, and deduplication."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("rag.vectorstore")


@dataclass
class VectorHit:
    id: str
    score: float
    payload: dict


class VectorStore:
    def __init__(self) -> None:
        self._client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )

    async def ensure_collection(self, name: str, dimension: int) -> None:
        existing = await self._client.collection_exists(name)
        if existing:
            return
        await self._client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=dimension, distance=models.Distance.COSINE
            ),
        )
        # Index the tenant_id + knowledge_base_id payload fields for fast filtering.
        for field in ("tenant_id", "knowledge_base_id", "document_id", "content_hash"):
            await self._client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

    async def upsert(self, collection: str, points: list[dict]) -> None:
        await self._client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
                for p in points
            ],
        )

    def _filter(self, tenant_id: str, extra: dict | None) -> models.Filter:
        must = [
            models.FieldCondition(
                key="tenant_id", match=models.MatchValue(value=str(tenant_id))
            )
        ]
        for key, value in (extra or {}).items():
            if value is None:
                continue
            must.append(
                models.FieldCondition(key=key, match=models.MatchValue(value=str(value)))
            )
        return models.Filter(must=must)

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        *,
        tenant_id: str,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> list[VectorHit]:
        """Tenant isolation is enforced here — every query is filtered by tenant_id."""
        results = await self._client.search(
            collection_name=collection,
            query_vector=query_vector,
            query_filter=self._filter(tenant_id, filters),
            limit=top_k,
            with_payload=True,
        )
        return [VectorHit(id=str(r.id), score=r.score, payload=r.payload or {}) for r in results]

    async def keyword_search(
        self,
        collection: str,
        text: str,
        *,
        tenant_id: str,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> list[VectorHit]:
        """Lightweight payload substring match (full-text). Augments semantic search."""
        flt = self._filter(tenant_id, filters)
        flt.must.append(
            models.FieldCondition(key="content", match=models.MatchText(text=text))
        )
        points, _ = await self._client.scroll(
            collection_name=collection, scroll_filter=flt, limit=top_k, with_payload=True
        )
        return [VectorHit(id=str(p.id), score=0.5, payload=p.payload or {}) for p in points]

    async def hybrid_search(
        self,
        collection: str,
        query_vector: list[float],
        text: str,
        *,
        tenant_id: str,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> list[VectorHit]:
        """Reciprocal-rank-fusion of semantic + keyword results."""
        semantic = await self.search(
            collection, query_vector, tenant_id=tenant_id, top_k=top_k * 2, filters=filters
        )
        try:
            keyword = await self.keyword_search(
                collection, text, tenant_id=tenant_id, top_k=top_k * 2, filters=filters
            )
        except Exception:  # MatchText needs a text index; degrade gracefully
            keyword = []
        return _rrf_merge(semantic, keyword, top_k)

    async def delete_document(self, collection: str, tenant_id: str, document_id: str) -> None:
        await self._client.delete(
            collection_name=collection,
            points_selector=models.FilterSelector(
                filter=self._filter(tenant_id, {"document_id": document_id})
            ),
        )

    async def content_hash_exists(
        self, collection: str, tenant_id: str, content_hash: str
    ) -> bool:
        points, _ = await self._client.scroll(
            collection_name=collection,
            scroll_filter=self._filter(tenant_id, {"content_hash": content_hash}),
            limit=1,
        )
        return len(points) > 0


def _rrf_merge(a: list[VectorHit], b: list[VectorHit], top_k: int, k: int = 60) -> list[VectorHit]:
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    for ranked in (a, b):
        for rank, hit in enumerate(ranked):
            scores[hit.id] = scores.get(hit.id, 0.0) + 1.0 / (k + rank + 1)
            payloads[hit.id] = hit.payload
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [VectorHit(id=i, score=s, payload=payloads[i]) for i, s in ordered]


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def new_point_id() -> str:
    return str(uuid.uuid4())
