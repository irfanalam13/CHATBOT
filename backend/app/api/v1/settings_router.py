"""Tenant profile + settings (LLM/embedding/RAG config, provider keys)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.rbac import Permission
from app.core.security import encrypt_value
from app.models.tenant import Tenant, TenantSettings
from app.repositories.repos import get_tenant_settings
from app.schemas.tenant import (
    TenantOut,
    TenantSettingsOut,
    TenantSettingsUpdate,
    TenantUpdate,
)

router = APIRouter(prefix="/tenant", tags=["tenant", "settings"])


@router.get("", response_model=TenantOut)
async def get_tenant(
    principal: Principal = Depends(require_permission(Permission.TENANT_READ)),
    db: AsyncSession = Depends(get_db),
) -> TenantOut:
    tenant = await db.get(Tenant, principal.tenant_id)
    return TenantOut.model_validate(tenant)


@router.patch("", response_model=TenantOut)
async def update_tenant(
    body: TenantUpdate,
    principal: Principal = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> TenantOut:
    tenant = await db.get(Tenant, principal.tenant_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)
    await db.flush()
    return TenantOut.model_validate(tenant)


@router.get("/settings", response_model=TenantSettingsOut)
async def get_settings(
    principal: Principal = Depends(require_permission(Permission.TENANT_READ)),
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsOut:
    ts = await get_tenant_settings(db, principal.tenant_id)
    if not ts:
        raise NotFoundError("Settings not found")
    return _to_out(ts)


@router.patch("/settings", response_model=TenantSettingsOut)
async def update_settings(
    body: TenantSettingsUpdate,
    principal: Principal = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsOut:
    ts = await get_tenant_settings(db, principal.tenant_id)
    if not ts:
        ts = TenantSettings(tenant_id=principal.tenant_id)
        db.add(ts)

    data = body.model_dump(exclude_unset=True)
    # Encrypt and store provider keys separately.
    for provider in ("anthropic", "openai", "google"):
        key = data.pop(f"{provider}_api_key", None)
        if key:
            setattr(ts, f"{provider}_api_key_enc", encrypt_value(key))
    for field, value in data.items():
        setattr(ts, field, value)
    await db.flush()
    return _to_out(ts)


def _to_out(ts: TenantSettings) -> TenantSettingsOut:
    return TenantSettingsOut(
        llm_provider=ts.llm_provider,
        llm_model=ts.llm_model,
        embedding_provider=ts.embedding_provider,
        embedding_model=ts.embedding_model,
        system_prompt=ts.system_prompt,
        chunk_strategy=ts.chunk_strategy,
        chunk_size=ts.chunk_size,
        chunk_overlap=ts.chunk_overlap,
        retrieval_top_k=ts.retrieval_top_k,
        enable_reranking=ts.enable_reranking,
        enable_tools=ts.enable_tools,
        has_anthropic_key=bool(ts.anthropic_api_key_enc),
        has_openai_key=bool(ts.openai_api_key_enc),
        has_google_key=bool(ts.google_api_key_enc),
    )
