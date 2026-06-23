"""Async SQLAlchemy engine, session factory and declarative base."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings
from app.core.db_types import UUID

_db_uri = settings.sqlalchemy_database_uri
_is_sqlite = _db_uri.startswith("sqlite")

# SQLite's async driver uses a pool that doesn't accept size/overflow args, so
# only pass the connection-pool tuning when running against a real server.
_engine_kwargs: dict = {
    "echo": settings.DEBUG and settings.ENVIRONMENT == "development",
    "pool_pre_ping": True,
}
if not _is_sqlite:
    _engine_kwargs.update(pool_size=20, max_overflow=10)

engine = create_async_engine(_db_uri, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


class Base(DeclarativeBase):
    """Declarative base with common id / timestamp columns."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
