"""Concrete repositories. Thin subclasses of TenantRepository plus a couple of
non-tenant-scoped helpers (users by email, refresh tokens)."""
from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import (
    ChatSession,
    Memory,
    MemoryScope,
    Message,
    MessageCitation,
)
from app.models.document import Document, DocumentChunk
from app.models.feedback import Feedback, ReviewQueueItem
from app.models.knowledge import KnowledgeBase
from app.models.tenant import Tenant, TenantSettings
from app.models.tool import ToolDefinition
from app.models.user import ApiKey, RefreshToken, User
from app.repositories.base import TenantRepository


class KnowledgeBaseRepo(TenantRepository[KnowledgeBase]):
    model = KnowledgeBase


class DocumentRepo(TenantRepository[Document]):
    model = Document


class ChunkRepo(TenantRepository[DocumentChunk]):
    model = DocumentChunk


class SessionRepo(TenantRepository[ChatSession]):
    model = ChatSession


class MessageRepo(TenantRepository[Message]):
    model = Message

    async def for_session(self, session_id: uuid.UUID) -> list[Message]:
        stmt = (
            self._scoped()
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def recent_for_session(
        self, session_id: uuid.UUID, limit: int
    ) -> list[Message]:
        """The last ``limit`` messages in chronological order.

        Bounds the query to the short-term window instead of materialising an
        entire (potentially thousands-long) transcript only to slice off the
        tail in Python. Served by the ``(session_id, created_at)`` index.
        """
        stmt = (
            self._scoped()
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(reversed(rows))


class CitationRepo(TenantRepository[MessageCitation]):
    model = MessageCitation


class MemoryRepo(TenantRepository[Memory]):
    model = Memory

    async def relevant(
        self, *, user_id: uuid.UUID, session_id: uuid.UUID, limit: int = 10
    ) -> list[Memory]:
        """Top-``limit`` memories in scope for this user/session, ranked by
        importance — scope filtering pushed into SQL (was: fetch 20, filter in
        Python, which could under-fill the result and scanned irrelevant rows)."""
        stmt = (
            self._scoped()
            .where(
                or_(
                    Memory.scope == MemoryScope.TENANT,
                    and_(Memory.scope == MemoryScope.USER, Memory.owner_id == user_id),
                    and_(
                        Memory.scope == MemoryScope.SESSION,
                        Memory.owner_id == session_id,
                    ),
                )
            )
            .order_by(Memory.importance.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class FeedbackRepo(TenantRepository[Feedback]):
    model = Feedback


class ReviewRepo(TenantRepository[ReviewQueueItem]):
    model = ReviewQueueItem


class ToolRepo(TenantRepository[ToolDefinition]):
    model = ToolDefinition

    async def active(self) -> list[ToolDefinition]:
        stmt = self._scoped().where(ToolDefinition.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class UserRepo(TenantRepository[User]):
    model = User

    async def by_email(self, email: str) -> User | None:
        stmt = self._scoped().where(User.email == email.lower())
        return (await self.session.execute(stmt)).scalar_one_or_none()


# ── Non-tenant-scoped helpers ─────────────────────────────────
async def get_tenant_by_slug(session: AsyncSession, slug: str) -> Tenant | None:
    res = await session.execute(select(Tenant).where(Tenant.slug == slug))
    return res.scalar_one_or_none()


async def get_tenant_settings(session: AsyncSession, tenant_id: uuid.UUID) -> TenantSettings | None:
    res = await session.execute(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


async def find_user_for_login(session: AsyncSession, tenant_id: uuid.UUID, email: str) -> User | None:
    res = await session.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == email.lower())
    )
    return res.scalar_one_or_none()


async def get_refresh_token(session: AsyncSession, jti: str) -> RefreshToken | None:
    res = await session.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    return res.scalar_one_or_none()


async def get_api_key_by_hash(session: AsyncSession, key_hash: str) -> ApiKey | None:
    res = await session.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    return res.scalar_one_or_none()
