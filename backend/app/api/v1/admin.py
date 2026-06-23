"""Platform (super-admin) endpoints: tenant lifecycle + cross-tenant overview."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.rbac import Permission
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.tenant import TenantOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tenants", response_model=list[TenantOut])
async def list_tenants(
    _: Principal = Depends(require_permission(Permission.ADMIN_PLATFORM)),
    db: AsyncSession = Depends(get_db),
) -> list[TenantOut]:
    rows = (await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))).scalars().all()
    return [TenantOut.model_validate(t) for t in rows]


@router.post("/tenants/{tenant_id}/suspend", response_model=MessageResponse)
async def suspend_tenant(
    tenant_id: uuid.UUID,
    _: Principal = Depends(require_permission(Permission.ADMIN_PLATFORM)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    tenant = await db.get(Tenant, tenant_id)
    if tenant:
        tenant.status = TenantStatus.SUSPENDED
        await db.flush()
    return MessageResponse(message="Tenant suspended")


@router.post("/tenants/{tenant_id}/activate", response_model=MessageResponse)
async def activate_tenant(
    tenant_id: uuid.UUID,
    _: Principal = Depends(require_permission(Permission.ADMIN_PLATFORM)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    tenant = await db.get(Tenant, tenant_id)
    if tenant:
        tenant.status = TenantStatus.ACTIVE
        await db.flush()
    return MessageResponse(message="Tenant activated")


@router.get("/overview")
async def platform_overview(
    _: Principal = Depends(require_permission(Permission.ADMIN_PLATFORM)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tenants = (await db.execute(select(func.count()).select_from(Tenant))).scalar_one()
    users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    return {"tenants": int(tenants), "users": int(users)}
