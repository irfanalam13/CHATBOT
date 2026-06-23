"""Tenant tool definitions for function calling (CRM/ERP/HR/etc.)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.core.rbac import Permission
from app.models.tool import ToolCategory, ToolDefinition
from app.repositories.repos import ToolRepo
from app.schemas.common import MessageResponse, Page
from app.schemas.tool import ToolCreate, ToolOut, ToolUpdate

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("", response_model=ToolOut, status_code=201)
async def create_tool(
    body: ToolCreate,
    principal: Principal = Depends(require_permission(Permission.TOOL_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> ToolOut:
    repo = ToolRepo(db, principal.tenant_id)
    tool = ToolDefinition(
        tenant_id=principal.tenant_id, name=body.name,
        category=ToolCategory(body.category), description=body.description,
        input_schema=body.input_schema, handler_type=body.handler_type,
        handler_config=body.handler_config,
    )
    try:
        await repo.add(tool)
    except Exception:
        raise ConflictError("Tool name already exists")
    return ToolOut.model_validate(tool)


@router.get("", response_model=Page[ToolOut])
async def list_tools(
    page: int = 1, page_size: int = 50,
    principal: Principal = Depends(require_permission(Permission.TOOL_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> Page[ToolOut]:
    rows, total = await ToolRepo(db, principal.tenant_id).list(
        offset=(page - 1) * page_size, limit=page_size
    )
    return Page(items=[ToolOut.model_validate(t) for t in rows], total=total,
                page=page, page_size=page_size)


@router.patch("/{tool_id}", response_model=ToolOut)
async def update_tool(
    tool_id: uuid.UUID, body: ToolUpdate,
    principal: Principal = Depends(require_permission(Permission.TOOL_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> ToolOut:
    repo = ToolRepo(db, principal.tenant_id)
    tool = await repo.get_or_404(tool_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tool, field, value)
    await db.flush()
    return ToolOut.model_validate(tool)


@router.delete("/{tool_id}", response_model=MessageResponse)
async def delete_tool(
    tool_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.TOOL_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = ToolRepo(db, principal.tenant_id)
    tool = await repo.get_or_404(tool_id)
    await repo.delete(tool)
    return MessageResponse(message="Tool deleted")
