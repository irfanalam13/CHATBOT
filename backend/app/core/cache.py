"""Tiny Redis-backed JSON cache.

Used to take repeated, cheap-but-frequent reads off the hot request path —
principal resolution (runs on *every* authenticated request) and analytics
aggregates (expensive, staleness-tolerant).

Every operation fails *open*: if Redis is unavailable the caller transparently
falls back to the database, exactly like the rate-limit middleware. A cache
miss must never turn into a failed request.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger("core.cache")

# Principals carry security-sensitive state (is_active, role, scopes). Keep the
# TTL short so revocation/role changes converge quickly even without an explicit
# invalidation hook; mutating endpoints also invalidate eagerly (see below).
PRINCIPAL_TTL = 30
# Analytics aggregates tolerate minute-scale staleness.
ANALYTICS_TTL = 60


def user_principal_key(user_id: uuid.UUID | str) -> str:
    return f"princ:user:{user_id}"


def apikey_principal_key(key_hash: str) -> str:
    return f"princ:key:{key_hash}"


async def cache_get_json(key: str) -> Any | None:
    try:
        raw = await get_redis().get(key)
    except Exception:  # Redis down → behave as a miss.
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    try:
        await get_redis().set(key, json.dumps(value), ex=ttl)
    except Exception:  # Caching is best-effort.
        pass


async def cache_delete(*keys: str) -> None:
    if not keys:
        return
    try:
        await get_redis().delete(*keys)
    except Exception:
        pass


async def invalidate_user_principal(user_id: uuid.UUID | str) -> None:
    """Drop a cached principal so a role/permission/activation change on a user
    takes effect on their next request rather than after the TTL."""
    await cache_delete(user_principal_key(user_id))
