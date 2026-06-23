"""Audit-log helper."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    action: str,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    status: str = "success",
    detail: dict | None = None,
) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            detail=detail or {},
        )
    )
    await session.flush()
