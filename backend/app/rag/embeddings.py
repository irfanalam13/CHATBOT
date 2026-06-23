"""Embedding providers: OpenAI, Google, BGE, E5, Instructor-XL, custom.

Local models (BGE/E5/Instructor) are loaded lazily and cached so that workers
don't pay the load cost on every call.
"""
from __future__ import annotations

import abc
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("rag.embeddings")


class Embedder(abc.ABC):
    dimension: int

    @abc.abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str, api_key: str, dimension: int):
        from openai import AsyncOpenAI

        self.model = model
        self.dimension = dimension
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


class GoogleEmbedder(Embedder):
    def __init__(self, model: str, api_key: str, dimension: int = 768):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self.model = model
        self.dimension = dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            r = self._genai.embed_content(model=self.model, content=t)
            out.append(r["embedding"])
        return out


class LocalEmbedder(Embedder):
    """Wraps a sentence-transformers model (BGE / E5 / Instructor / custom)."""

    def __init__(self, model_name: str, dimension: int, prefix: str = ""):
        self.model_name = model_name
        self.dimension = dimension
        self.prefix = prefix  # e5 wants "query: " / "passage: " prefixes
        self._model = _load_st_model(model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = [f"{self.prefix}{t}" for t in texts] if self.prefix else texts
        # sentence-transformers is sync; fine inside Celery workers / threadpool.
        vectors = self._model.encode(payload, normalize_embeddings=True)
        return [v.tolist() for v in vectors]


@lru_cache(maxsize=4)
def _load_st_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    log.info("loading_local_embedding_model", model=model_name)
    return SentenceTransformer(model_name)


_LOCAL_MODELS = {
    "bge": ("BAAI/bge-large-en-v1.5", 1024, ""),
    "e5": ("intfloat/e5-large-v2", 1024, "passage: "),
    "instructor": ("hkunlp/instructor-xl", 768, ""),
}


def get_embedder(
    provider: str | None = None,
    model: str | None = None,
    *,
    api_keys: dict[str, str] | None = None,
) -> Embedder:
    provider = provider or settings.DEFAULT_EMBEDDING_PROVIDER
    api_keys = api_keys or {}

    if provider == "openai":
        return OpenAIEmbedder(
            model or settings.DEFAULT_EMBEDDING_MODEL,
            api_keys.get("openai") or settings.OPENAI_API_KEY,
            settings.EMBEDDING_DIMENSION,
        )
    if provider == "google":
        return GoogleEmbedder(
            model or settings.DEFAULT_EMBEDDING_MODEL or "models/gemini-embedding-001",
            api_keys.get("google") or settings.GOOGLE_API_KEY,
            settings.EMBEDDING_DIMENSION,
        )
    if provider in _LOCAL_MODELS:
        name, dim, prefix = _LOCAL_MODELS[provider]
        return LocalEmbedder(model or name, dim, prefix)
    if provider == "custom" and model:
        return LocalEmbedder(model, settings.EMBEDDING_DIMENSION)
    raise ValueError(f"Unknown embedding provider: {provider}")
