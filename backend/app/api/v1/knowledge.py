"""Knowledge base CRUD."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.rbac import Permission
from app.models.knowledge import KnowledgeBase
from app.repositories.repos import KnowledgeBaseRepo
from app.schemas.common import MessageResponse, Page
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])


@router.post("", response_model=KnowledgeBaseOut, status_code=201)
async def create_kb(
    body: KnowledgeBaseCreate,
    principal: Principal = Depends(require_permission(Permission.KB_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    kb = KnowledgeBase(
        tenant_id=principal.tenant_id, name=body.name, slug=body.slug,
        description=body.description, config=body.config,
    )
    await KnowledgeBaseRepo(db, principal.tenant_id).add(kb)
    return KnowledgeBaseOut.model_validate(kb)


@router.get("", response_model=Page[KnowledgeBaseOut])
async def list_kb(
    page: int = 1, page_size: int = 20,
    principal: Principal = Depends(require_permission(Permission.KB_READ)),
    db: AsyncSession = Depends(get_db),
) -> Page[KnowledgeBaseOut]:
    rows, total = await KnowledgeBaseRepo(db, principal.tenant_id).list(
        offset=(page - 1) * page_size, limit=page_size
    )
    return Page(items=[KnowledgeBaseOut.model_validate(r) for r in rows], total=total,
                page=page, page_size=page_size)


@router.get("/{kb_id}", response_model=KnowledgeBaseOut)
async def get_kb(
    kb_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.KB_READ)),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    kb = await KnowledgeBaseRepo(db, principal.tenant_id).get_or_404(kb_id)
    return KnowledgeBaseOut.model_validate(kb)


@router.patch("/{kb_id}", response_model=KnowledgeBaseOut)
async def update_kb(
    kb_id: uuid.UUID, body: KnowledgeBaseUpdate,
    principal: Principal = Depends(require_permission(Permission.KB_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeBaseOut:
    repo = KnowledgeBaseRepo(db, principal.tenant_id)
    kb = await repo.get_or_404(kb_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(kb, field, value)
    await db.flush()
    return KnowledgeBaseOut.model_validate(kb)


@router.delete("/{kb_id}", response_model=MessageResponse)
async def delete_kb(
    kb_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.KB_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = KnowledgeBaseRepo(db, principal.tenant_id)
    kb = await repo.get_or_404(kb_id)
    await repo.delete(kb)
    return MessageResponse(message="Knowledge base deleted")
