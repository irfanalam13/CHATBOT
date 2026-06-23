"""Enterprise search endpoints."""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.rbac import Permission
from app.schemas.search import GlobalSearchResponse, SearchRequest, SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/documents", response_model=SearchResponse)
async def search_documents(
    body: SearchRequest,
    principal: Principal = Depends(require_permission(Permission.SEARCH_USE)),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    return await SearchService(db, principal.tenant_id).search_documents(body)


@router.get("/chats")
async def search_chats(
    q: str, limit: int = 20,
    principal: Principal = Depends(require_permission(Permission.SEARCH_USE)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await SearchService(db, principal.tenant_id).search_chats(q, principal.user_id, limit)


@router.post("/global", response_model=GlobalSearchResponse)
async def global_search(
    body: SearchRequest,
    principal: Principal = Depends(require_permission(Permission.SEARCH_USE)),
    db: AsyncSession = Depends(get_db),
) -> GlobalSearchResponse:
    start = time.perf_counter()
    svc = SearchService(db, principal.tenant_id)
    docs = await svc.search_documents(body)
    chats = await svc.search_chats(body.query, principal.user_id) if principal.user_id else []
    return GlobalSearchResponse(
        query=body.query, documents=docs.hits, chats=chats,
        took_ms=int((time.perf_counter() - start) * 1000),
    )
