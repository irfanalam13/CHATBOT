"""Generic tenant-scoped repository.

Every query made through this base is constrained by ``tenant_id`` so that no
service can accidentally read or mutate another tenant's rows — the core
multi-tenancy isolation guarantee.
"""
from __future__ import annotations

import uuid
from typing import Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.core.exceptions import NotFoundError

ModelT = TypeVar("ModelT", bound=Base)


class TenantRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    def _scoped(self):
        return select(self.model).where(self.model.tenant_id == self.tenant_id)

    async def get(self, id_: uuid.UUID) -> ModelT | None:
        res = await self.session.execute(self._scoped().where(self.model.id == id_))
        return res.scalar_one_or_none()

    async def get_or_404(self, id_: uuid.UUID) -> ModelT:
        obj = await self.get(id_)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} not found")
        return obj

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        order_by=None,
        filters: list | None = None,
    ) -> tuple[Sequence[ModelT], int]:
        stmt = self._scoped()
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            stmt = stmt.order_by(self.model.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return rows, total

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
