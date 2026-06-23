"""Application configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_db_url(raw: str, *, driver: Literal["asyncpg", "psycopg2"]) -> str:
    """Return `raw` with an explicit SQLAlchemy driver and driver-appropriate
    connection params.

    A bare ``postgresql://`` URL (e.g. a Neon connection string) has no
    SQLAlchemy driver, so ``create_async_engine`` would reject it. We force the
    right driver and reconcile TLS query params, which differ per driver:

    * ``asyncpg`` does not accept libpq's ``sslmode`` / ``channel_binding`` —
      it uses ``ssl=`` — so we translate them. We also disable the prepared
      statement cache, required when talking to a PgBouncer transaction-mode
      pooler such as Neon's ``-pooler`` endpoint.
    * ``psycopg2`` speaks libpq, so ``sslmode`` / ``channel_binding`` pass
      straight through.
    """
    parts = urlsplit(raw)
    if parts.scheme.startswith("sqlite"):
        return raw

    new_scheme = f"postgresql+{driver}"
    query = dict(parse_qsl(parts.query, keep_blank_values=True))

    if driver == "asyncpg":
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        if sslmode and sslmode != "disable":
            query.setdefault("ssl", "require")
        # Neon's pooled endpoint runs PgBouncer in transaction mode, which is
        # incompatible with asyncpg's server-side prepared statements.
        if "pooler" in parts.netloc:
            query.setdefault("prepared_statement_cache_size", "0")

    return urlunsplit(
        (new_scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── Application ────────────────────────────────────────────
    APP_NAME: str = "Enterprise AI Chatbot Platform"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me"
    ENCRYPTION_KEY: str = "change-me-fernet-key"

    # ── CORS ───────────────────────────────────────────────────
    # Comma-separated list of frontend origins allowed to call the API in
    # production (when DEBUG is false). e.g.
    # "https://app.example.com,https://chatbot.example.com".
    # In DEBUG mode all origins are allowed regardless of this value.
    CORS_ORIGINS: str = ""

    # ── JWT ────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── PostgreSQL ─────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "chatbot"
    POSTGRES_PASSWORD: str = "chatbot"
    POSTGRES_DB: str = "chatbot"
    DATABASE_URL: str | None = None

    # ── Redis / Celery ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Qdrant ─────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # ── Object storage ─────────────────────────────────────────
    S3_ENDPOINT_URL: str | None = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "chatbot-documents"
    S3_REGION: str = "us-east-1"

    # ── LLM providers ──────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: Literal["anthropic", "openai", "google"] = "anthropic"
    DEFAULT_LLM_MODEL: str = "claude-opus-4-8"

    # ── Embeddings ─────────────────────────────────────────────
    DEFAULT_EMBEDDING_PROVIDER: str = "openai"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # ── RAG ────────────────────────────────────────────────────
    DEFAULT_CHUNK_STRATEGY: str = "recursive"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 120
    RETRIEVAL_TOP_K: int = 8
    RERANK_TOP_N: int = 4
    ENABLE_RERANKING: bool = True

    # ── Rate limiting ──────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 120

    # ── Observability ──────────────────────────────────────────
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # ── Misc ───────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_UPLOAD_EXTENSIONS: tuple[str, ...] = (
        ".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls",
        ".html", ".htm", ".md", ".json", ".xml", ".eml",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a clean list of origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.DATABASE_URL:
            return _normalize_db_url(self.DATABASE_URL, driver="asyncpg")
        # URL-encode credentials so special characters (e.g. "@", ":", "/") in
        # the user/password don't corrupt the URL's authority section.
        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def alembic_database_uri(self) -> str:
        """Sync driver for migrations."""
        if self.DATABASE_URL:
            return _normalize_db_url(self.DATABASE_URL, driver="psycopg2")
        return self.sqlalchemy_database_uri.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
