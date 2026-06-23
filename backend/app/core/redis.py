"""Shared async Redis client (cache + short-term memory + rate-limit store)."""
from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL, decode_responses=True, max_connections=50
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


async def close_redis() -> None:
    await _pool.disconnect()
