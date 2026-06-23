"""Feedback + review queue schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    message_id: uuid.UUID
    feedback_type: str  # thumbs_up | thumbs_down | correction
    comment: str | None = None
    correction: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID
    feedback_type: str
    comment: str | None
    correction: str | None
    created_at: datetime


class ReviewItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message_id: uuid.UUID | None
    reason: str
    status: str
    assigned_to: uuid.UUID | None
    resolution: str | None
    created_at: datetime


class ReviewUpdate(BaseModel):
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    resolution: str | None = None
