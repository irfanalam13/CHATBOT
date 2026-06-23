"""FastAPI application factory + lifespan + observability wiring."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from app.api.middleware import (
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis

log = get_logger("main")

REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "path"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1,
                        environment=settings.ENVIRONMENT)
    log.info("startup", app=settings.APP_NAME, env=settings.ENVIRONMENT)
    try:
        yield
    finally:
        await close_redis()
        log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description="Enterprise multi-tenant AI chatbot platform with RAG, "
                    "tool calling, RBAC and full observability.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware (order matters: outermost first).
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    # In DEBUG allow all origins for convenience; in production restrict to the
    # explicit frontend origins from CORS_ORIGINS. Note: browsers reject the
    # "*" wildcard when credentials are sent, so production must list origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.DEBUG else settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    async def root() -> dict:
        return {"name": settings.APP_NAME, "version": "1.0.0", "docs": "/docs"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # OpenTelemetry tracing (best-effort).
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception:  # pragma: no cover
        pass

    return app


app = create_app()
