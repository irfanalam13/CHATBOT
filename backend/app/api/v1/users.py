"""User management within a tenant."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.cache import invalidate_user_principal
from app.core.database import get_db
from app.core.exceptions import ConflictError
from app.core.rbac import Permission
from app.core.security import hash_password
from app.models.user import User
from app.repositories.repos import UserRepo
from app.schemas.common import MessageResponse, Page
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    principal: Principal = Depends(require_permission(Permission.USER_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    repo = UserRepo(db, principal.tenant_id)
    if await repo.by_email(body.email):
        raise ConflictError("Email already registered in this tenant")
    user = User(
        tenant_id=principal.tenant_id, email=body.email.lower(), full_name=body.full_name,
        hashed_password=hash_password(body.password), role=body.role,
        custom_permissions=body.custom_permissions,
    )
    await repo.add(user)
    return UserOut.model_validate(user)


@router.get("", response_model=Page[UserOut])
async def list_users(
    page: int = 1, page_size: int = 20,
    principal: Principal = Depends(require_permission(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
) -> Page[UserOut]:
    rows, total = await UserRepo(db, principal.tenant_id).list(
        offset=(page - 1) * page_size, limit=page_size
    )
    return Page(items=[UserOut.model_validate(u) for u in rows], total=total,
                page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.USER_READ)),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = await UserRepo(db, principal.tenant_id).get_or_404(user_id)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID, body: UserUpdate,
    principal: Principal = Depends(require_permission(Permission.USER_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    repo = UserRepo(db, principal.tenant_id)
    user = await repo.get_or_404(user_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await invalidate_user_principal(user_id)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.USER_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = UserRepo(db, principal.tenant_id)
    user = await repo.get_or_404(user_id)
    user.is_active = False  # soft-deactivate
    await db.flush()
    await invalidate_user_principal(user_id)  # revoke access immediately
    return MessageResponse(message="User deactivated")
