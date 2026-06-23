"""Aggregate every v1 router under one APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    analytics,
    auth,
    chat,
    documents,
    feedback,
    health,
    knowledge,
    search,
    settings_router,
    tools,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(settings_router.router)
api_router.include_router(users.router)
api_router.include_router(knowledge.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(search.router)
api_router.include_router(analytics.router)
api_router.include_router(feedback.router)
api_router.include_router(tools.router)
api_router.include_router(admin.router)
