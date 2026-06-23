"""Liveness / readiness probes."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict:
    checks = {"database": False, "redis": False}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass
    try:
        await get_redis().ping()
        checks["redis"] = True
    except Exception:
        pass
    return {"status": "ok" if all(checks.values()) else "degraded", "checks": checks}
