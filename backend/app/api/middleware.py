"""Cross-cutting HTTP middleware: request id, structured access logs,
Redis-backed rate limiting, and basic security headers."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            took = int((time.perf_counter() - start) * 1000)
            log.info(
                "request",
                method=request.method,
                path=request.url.path,
                took_ms=took,
            )
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-identity rate limit backed by Redis."""

    EXEMPT = ("/api/v1/health", "/api/v1/ready", "/docs", "/openapi.json", "/redoc")

    async def dispatch(self, request: Request, call_next):
        if any(request.url.path.startswith(p) for p in self.EXEMPT):
            return await call_next(request)

        identity = self._identity(request)
        key = f"rl:{identity}:{int(time.time() // 60)}"
        try:
            r = get_redis()
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, 60)
            if count > settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=429,
                    content={"error": {"code": "rate_limited", "message": "Too many requests"}},
                    headers={"Retry-After": "60"},
                )
        except Exception:  # Redis down → fail open rather than block all traffic
            pass
        return await call_next(request)

    @staticmethod
    def _identity(request: Request) -> str:
        api_key = request.headers.get("x-api-key")
        if api_key:
            return f"key:{api_key[:12]}"
        auth = request.headers.get("authorization", "")
        if auth:
            return f"jwt:{auth[-16:]}"
        fwd = request.headers.get("x-forwarded-for")
        return f"ip:{(fwd or (request.client.host if request.client else 'anon'))}"
