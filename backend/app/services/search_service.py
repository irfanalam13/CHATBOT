"""Enterprise search: semantic / keyword / hybrid / metadata over documents,
plus chat-history search and a combined global search."""
from __future__ import annotations

import time
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.chat import ChatSession, Message
from app.models.tenant import Tenant
from app.rag.retrieval import Retriever
from app.repositories.repos import get_tenant_settings
from app.schemas.search import SearchHit, SearchRequest, SearchResponse


class SearchService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def search_documents(self, req: SearchRequest) -> SearchResponse:
        start = time.perf_counter()
        tenant = await self.session.get(Tenant, self.tenant_id)
        ts = await get_tenant_settings(self.session, self.tenant_id)
        from app.services.ingestion_service import _tenant_embedding_keys

        retriever = Retriever(
            ts.embedding_provider if ts else None,
            ts.embedding_model if ts else None,
            api_keys=_tenant_embedding_keys(ts),
        )
        filters = dict(req.filters or {})
        if req.knowledge_base_id:
            filters["knowledge_base_id"] = str(req.knowledge_base_id)

        result = await retriever.retrieve(
            collection=tenant.vector_collection,
            tenant_id=str(self.tenant_id),
            query=req.query,
            mode=req.mode,
            top_k=req.top_k,
            rerank_enabled=req.rerank,
            filters=filters,
        )
        hits = [
            SearchHit(
                chunk_id=uuid.UUID(c.chunk_id) if c.chunk_id else None,
                document_id=uuid.UUID(c.document_id) if c.document_id else None,
                document_name=c.document_name,
                content=c.content,
                score=c.score,
                page_number=c.page_number,
                metadata=c.metadata,
            )
            for c in result.chunks
        ]
        return SearchResponse(
            query=req.query, mode=req.mode, hits=hits,
            took_ms=int((time.perf_counter() - start) * 1000),
        )

    async def search_chats(self, query: str, user_id: uuid.UUID, limit: int = 20) -> list[dict]:
        """Full-text-ish search over the user's own chat history."""
        stmt = (
            select(ChatSession, Message)
            .join(Message, Message.session_id == ChatSession.id)
            .where(
                ChatSession.tenant_id == self.tenant_id,
                ChatSession.user_id == user_id,
                or_(
                    ChatSession.title.ilike(f"%{query}%"),
                    Message.content.ilike(f"%{query}%"),
                ),
            )
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        out = []
        for chat, msg in rows:
            out.append(
                {
                    "session_id": str(chat.id),
                    "title": chat.title,
                    "snippet": msg.content[:200],
                    "role": msg.role.value,
                }
            )
        return out
