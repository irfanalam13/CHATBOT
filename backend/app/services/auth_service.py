"""Authentication: tenant registration, login, refresh-token rotation, logout."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError, ConflictError
from app.core.rbac import Role
from app.core.security import (
    REFRESH_TOKEN,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.tenant import Tenant, TenantSettings, TenantStatus
from app.models.user import RefreshToken, User
from app.repositories.repos import (
    find_user_for_login,
    get_refresh_token,
    get_tenant_by_slug,
)
from app.schemas.auth import LoginRequest, RegisterTenantRequest, TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register_tenant(self, req: RegisterTenantRequest) -> tuple[Tenant, User]:
        if await get_tenant_by_slug(self.session, req.tenant_slug):
            raise ConflictError("Tenant slug already taken")

        tenant = Tenant(
            name=req.tenant_name,
            slug=req.tenant_slug,
            status=TenantStatus.TRIAL,
            vector_collection=f"tenant_{req.tenant_slug}",
        )
        self.session.add(tenant)
        await self.session.flush()

        self.session.add(TenantSettings(tenant_id=tenant.id))

        admin = User(
            tenant_id=tenant.id,
            email=req.admin_email.lower(),
            full_name=req.admin_full_name,
            hashed_password=hash_password(req.admin_password),
            role=Role.TENANT_ADMIN.value,
        )
        self.session.add(admin)
        await self.session.flush()
        return tenant, admin

    async def login(self, req: LoginRequest, *, ip: str | None, ua: str | None) -> TokenResponse:
        tenant = await get_tenant_by_slug(self.session, req.tenant_slug)
        if not tenant or tenant.status == TenantStatus.SUSPENDED:
            raise AuthError("Invalid credentials")
        user = await find_user_for_login(self.session, tenant.id, req.email)
        if not user or not user.is_active or not verify_password(req.password, user.hashed_password):
            raise AuthError("Invalid credentials")

        user.last_login_at = datetime.now(timezone.utc)
        return await self._issue_tokens(user, ip=ip, ua=ua)

    async def refresh(self, token: str, *, ip: str | None, ua: str | None) -> TokenResponse:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            raise AuthError("Invalid refresh token")
        if payload.get("type") != REFRESH_TOKEN:
            raise AuthError("Not a refresh token")

        record = await get_refresh_token(self.session, payload["jti"])
        if not record or record.token_hash != hash_token(token):
            raise AuthError("Refresh token not recognised")
        if record.revoked:
            # Reuse of a rotated token → revoke the whole chain (breach response).
            await self._revoke_descendants(record)
            raise AuthError("Refresh token reuse detected")
        if record.expires_at < datetime.now(timezone.utc):
            raise AuthError("Refresh token expired")

        user = await self.session.get(User, record.user_id)
        if not user or not user.is_active:
            raise AuthError("User inactive")

        # Rotate: revoke the old token and issue a fresh pair.
        new = await self._issue_tokens(user, ip=ip, ua=ua)
        record.revoked = True
        return new

    async def logout(self, token: str) -> None:
        try:
            payload = decode_token(token)
        except jwt.PyJWTError:
            return
        record = await get_refresh_token(self.session, payload.get("jti", ""))
        if record:
            record.revoked = True

    # ── internals ─────────────────────────────────────────────
    async def _issue_tokens(self, user: User, *, ip: str | None, ua: str | None) -> TokenResponse:
        access = create_access_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            role=user.role,
            scopes=user.custom_permissions,
        )
        refresh_jwt, jti = create_refresh_token(
            user_id=str(user.id), tenant_id=str(user.tenant_id)
        )
        self.session.add(
            RefreshToken(
                tenant_id=user.tenant_id,
                user_id=user.id,
                jti=jti,
                token_hash=hash_token(refresh_jwt),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
                ip_address=ip,
                user_agent=ua,
            )
        )
        await self.session.flush()
        return TokenResponse(
            access_token=access,
            refresh_token=refresh_jwt,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def _revoke_descendants(self, record: RefreshToken) -> None:
        cur: RefreshToken | None = record
        seen: set[str] = set()
        while cur and cur.replaced_by and cur.replaced_by not in seen:
            seen.add(cur.replaced_by)
            cur.revoked = True
            cur = await get_refresh_token(self.session, cur.replaced_by)
        if cur:
            cur.revoked = True
