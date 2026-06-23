"""Feedback loop: thumbs / corrections + human review queue."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.database import get_db
from app.core.rbac import Permission
from app.models.feedback import (
    Feedback,
    FeedbackType,
    ReviewQueueItem,
    ReviewStatus,
)
from app.repositories.repos import FeedbackRepo, MessageRepo, ReviewRepo
from app.schemas.common import MessageResponse, Page
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackOut,
    ReviewItemOut,
    ReviewUpdate,
)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=201)
async def submit_feedback(
    body: FeedbackCreate,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> FeedbackOut:
    await MessageRepo(db, principal.tenant_id).get_or_404(body.message_id)
    fb = Feedback(
        tenant_id=principal.tenant_id, user_id=principal.user_id,
        message_id=body.message_id, feedback_type=FeedbackType(body.feedback_type),
        comment=body.comment, correction=body.correction,
    )
    await FeedbackRepo(db, principal.tenant_id).add(fb)

    # Route negative / correction feedback to the human review queue.
    if body.feedback_type in (FeedbackType.THUMBS_DOWN.value, FeedbackType.CORRECTION.value):
        db.add(
            ReviewQueueItem(
                tenant_id=principal.tenant_id, message_id=body.message_id,
                feedback_id=fb.id, reason=f"user_{body.feedback_type}",
            )
        )
        await db.flush()
    return FeedbackOut.model_validate(fb)


@router.get("/review-queue", response_model=Page[ReviewItemOut])
async def review_queue(
    page: int = 1, page_size: int = 20, status: str | None = None,
    principal: Principal = Depends(require_permission(Permission.FEEDBACK_REVIEW)),
    db: AsyncSession = Depends(get_db),
) -> Page[ReviewItemOut]:
    repo = ReviewRepo(db, principal.tenant_id)
    filters = []
    if status:
        filters.append(ReviewQueueItem.status == ReviewStatus(status))
    rows, total = await repo.list(offset=(page - 1) * page_size, limit=page_size, filters=filters)
    return Page(items=[ReviewItemOut.model_validate(r) for r in rows], total=total,
                page=page, page_size=page_size)


@router.patch("/review-queue/{item_id}", response_model=ReviewItemOut)
async def update_review(
    item_id: uuid.UUID, body: ReviewUpdate,
    principal: Principal = Depends(require_permission(Permission.FEEDBACK_REVIEW)),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemOut:
    repo = ReviewRepo(db, principal.tenant_id)
    item = await repo.get_or_404(item_id)
    if body.status is not None:
        item.status = ReviewStatus(body.status)
    if body.assigned_to is not None:
        item.assigned_to = body.assigned_to
    if body.resolution is not None:
        item.resolution = body.resolution
    await db.flush()
    return ReviewItemOut.model_validate(item)
