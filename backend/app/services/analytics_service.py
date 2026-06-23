"""Analytics + token/cost ledger writes and aggregate reads."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import ANALYTICS_TTL, cache_get_json, cache_set_json
from app.llm.pricing import estimate_cost
from app.models.analytics import AnalyticsEvent, TokenUsage


class AnalyticsService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def record(
        self, event_type: str, *, user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None, payload: dict | None = None,
    ) -> None:
        self.session.add(
            AnalyticsEvent(
                tenant_id=self.tenant_id, user_id=user_id, event_type=event_type,
                session_id=session_id, payload=payload or {},
            )
        )
        await self.session.flush()

    async def record_usage(
        self, *, user_id: uuid.UUID | None, message_id: uuid.UUID | None,
        provider: str, model: str, prompt_tokens: int, completion_tokens: int,
        operation: str = "chat", latency_ms: int | None = None,
    ) -> None:
        self.session.add(
            TokenUsage(
                tenant_id=self.tenant_id, user_id=user_id, message_id=message_id,
                provider=provider, model=model, operation=operation,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=estimate_cost(model, prompt_tokens, completion_tokens),
                latency_ms=latency_ms,
            )
        )
        await self.session.flush()

    async def dashboard(self, days: int = 30) -> dict:
        # Dashboards are read far more often than the underlying events change,
        # and tolerate minute-scale staleness — serve from cache when warm.
        cache_key = f"analytics:dash:{self.tenant_id}:{days}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return cached

        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Token/cost ledger: one scan of token_usage.
        usage = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(TokenUsage.total_tokens), 0),
                    func.coalesce(func.sum(TokenUsage.cost_usd), 0.0),
                    func.coalesce(func.avg(TokenUsage.latency_ms), 0),
                ).where(
                    TokenUsage.tenant_id == self.tenant_id,
                    TokenUsage.created_at >= since,
                )
            )
        ).one()

        # Event metrics: a single scan of analytics_events with conditional
        # aggregation, replacing three separate full-table counts.
        events = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.sum(
                            case((AnalyticsEvent.event_type == "question_asked", 1), else_=0)
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(
                            case((AnalyticsEvent.event_type == "search_failed", 1), else_=0)
                        ),
                        0,
                    ),
                    func.count(func.distinct(AnalyticsEvent.user_id)),
                ).where(
                    AnalyticsEvent.tenant_id == self.tenant_id,
                    AnalyticsEvent.created_at >= since,
                )
            )
        ).one()

        result = {
            "window_days": days,
            "total_tokens": int(usage[0]),
            "total_cost_usd": round(float(usage[1]), 4),
            "avg_latency_ms": int(usage[2] or 0),
            "questions_asked": int(events[0]),
            "failed_searches": int(events[1]),
            "active_users": int(events[2]),
        }
        await cache_set_json(cache_key, result, ANALYTICS_TTL)
        return result
