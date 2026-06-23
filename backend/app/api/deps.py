"""Request-scoped dependencies: authenticated principal, tenant context, RBAC."""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    PRINCIPAL_TTL,
    apikey_principal_key,
    cache_get_json,
    cache_set_json,
    user_principal_key,
)
from app.core.database import get_db
from app.core.exceptions import AuthError, ForbiddenError
from app.core.rbac import Permission, has_permission
from app.core.security import ACCESS_TOKEN, decode_token, hash_token
from app.models.user import User
from app.repositories.repos import get_api_key_by_hash

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: uuid.UUID | None
    tenant_id: uuid.UUID
    role: str
    scopes: list[str]
    is_api_key: bool = False

    def require(self, permission: Permission) -> None:
        if not has_permission(self.role, permission, set(self.scopes)):
            raise ForbiddenError(f"Missing permission: {permission.value}")

    # ── (de)serialisation for the principal cache ──────────────
    def _to_cache(self) -> dict:
        return {
            "user_id": str(self.user_id) if self.user_id else None,
            "tenant_id": str(self.tenant_id),
            "role": self.role,
            "scopes": self.scopes,
            "is_api_key": self.is_api_key,
        }

    @classmethod
    def _from_cache(cls, d: dict) -> "Principal":
        return cls(
            user_id=uuid.UUID(d["user_id"]) if d.get("user_id") else None,
            tenant_id=uuid.UUID(d["tenant_id"]),
            role=d["role"],
            scopes=d.get("scopes") or [],
            is_api_key=d.get("is_api_key", False),
        )


async def get_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    # 1. API-key auth (tenant-scoped programmatic access).
    # Cached by key hash so the per-request validation is a single Redis GET
    # instead of an indexed-but-still-remote Postgres lookup.
    if x_api_key:
        key_hash = hash_token(x_api_key)
        cache_key = apikey_principal_key(key_hash)
        cached = await cache_get_json(cache_key)
        if cached:
            return Principal._from_cache(cached)
        record = await get_api_key_by_hash(db, key_hash)
        if not record:
            raise AuthError("Invalid API key")
        principal = Principal(
            user_id=None, tenant_id=record.tenant_id,
            role="tenant_admin", scopes=record.scopes, is_api_key=True,
        )
        await cache_set_json(cache_key, principal._to_cache(), PRINCIPAL_TTL)
        return principal

    # 2. Bearer JWT.
    if not creds:
        raise AuthError("Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.PyJWTError:
        raise AuthError("Invalid token")
    if payload.get("type") != ACCESS_TOKEN:
        raise AuthError("Not an access token")

    user_id = uuid.UUID(payload["sub"])
    cache_key = user_principal_key(user_id)
    # The signed token has already been verified above; the only thing the DB
    # read adds is current role/scopes/is_active, which we cache briefly.
    cached = await cache_get_json(cache_key)
    if cached:
        principal = Principal._from_cache(cached)
        # Defence in depth: token tenant must match the cached principal's.
        if str(principal.tenant_id) != payload["tenant_id"]:
            raise ForbiddenError("Tenant mismatch")
        return principal

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise AuthError("User inactive")
    # Defence in depth: token tenant must match the user's tenant.
    if str(user.tenant_id) != payload["tenant_id"]:
        raise ForbiddenError("Tenant mismatch")

    principal = Principal(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role,
        scopes=user.custom_permissions or [],
    )
    # Only active users reach here, so the cached entry always represents an
    # authorised principal; invalidated eagerly on user mutation (api/v1/users).
    await cache_set_json(cache_key, principal._to_cache(), PRINCIPAL_TTL)
    return principal


def require_permission(permission: Permission):
    async def _dep(principal: Principal = Depends(get_principal)) -> Principal:
        principal.require(permission)
        return principal

    return _dep


def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None
