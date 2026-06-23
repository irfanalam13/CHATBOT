"""Analytics dashboard + popular topics + token/cost reporting."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.rbac import Permission
from app.models.analytics import TokenUsage
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(
    days: int = 30,
    principal: Principal = Depends(require_permission(Permission.ANALYTICS_READ)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await AnalyticsService(db, principal.tenant_id).dashboard(days)


@router.get("/cost-by-model")
async def cost_by_model(
    principal: Principal = Depends(require_permission(Permission.ANALYTICS_READ)),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    stmt = (
        select(
            TokenUsage.model,
            func.sum(TokenUsage.total_tokens),
            func.sum(TokenUsage.cost_usd),
            func.count(),
        )
        .where(TokenUsage.tenant_id == principal.tenant_id)
        .group_by(TokenUsage.model)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"model": r[0], "tokens": int(r[1]), "cost_usd": round(float(r[2]), 4), "calls": r[3]}
        for r in rows
    ]
