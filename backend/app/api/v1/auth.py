"""Auth endpoints: tenant registration, login, refresh, logout, me."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, client_ip, get_principal
from app.core.database import get_db
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterTenantRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserOut
from app.services.audit import write_audit
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterTenantRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    tenant, admin = await service.register_tenant(body)
    await write_audit(
        db, action="tenant.register", tenant_id=tenant.id, user_id=admin.id,
        ip_address=client_ip(request), resource_type="tenant", resource_id=str(tenant.id),
    )
    return await service._issue_tokens(
        admin, ip=client_ip(request), ua=request.headers.get("user-agent")
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    tokens = await service.login(
        body, ip=client_ip(request), ua=request.headers.get("user-agent")
    )
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    return await service.refresh(
        body.refresh_token, ip=client_ip(request), ua=request.headers.get("user-agent")
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await AuthService(db).logout(body.refresh_token)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserOut)
async def me(
    principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db)
) -> UserOut:
    from app.models.user import User

    user = await db.get(User, principal.user_id)
    return UserOut.model_validate(user)
