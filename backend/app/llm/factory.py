"""Construct an LLM provider from platform defaults + per-tenant overrides."""
from __future__ import annotations

from app.core.config import settings
from app.core.security import decrypt_value
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMProvider
from app.llm.google_provider import GoogleProvider
from app.llm.openai_provider import OpenAIProvider
from app.models.tenant import TenantSettings

_PLATFORM_KEYS = {
    "anthropic": settings.ANTHROPIC_API_KEY,
    "openai": settings.OPENAI_API_KEY,
    "google": settings.GOOGLE_API_KEY,
}

_DEFAULT_MODELS = {
    "anthropic": "claude-opus-4-8",
    "openai": "gpt-4o",
    "google": "gemini-2.5-flash",
}


def _tenant_key(ts: TenantSettings | None, provider: str) -> str | None:
    if not ts:
        return None
    enc = {
        "anthropic": ts.anthropic_api_key_enc,
        "openai": ts.openai_api_key_enc,
        "google": ts.google_api_key_enc,
    }.get(provider)
    return decrypt_value(enc) if enc else None


def get_llm_provider(tenant_settings: TenantSettings | None = None) -> LLMProvider:
    provider = (
        (tenant_settings.llm_provider if tenant_settings else None)
        or settings.DEFAULT_LLM_PROVIDER
    )
    model = (
        (tenant_settings.llm_model if tenant_settings else None)
        or (settings.DEFAULT_LLM_MODEL if provider == "anthropic" else _DEFAULT_MODELS[provider])
    )
    api_key = _tenant_key(tenant_settings, provider) or _PLATFORM_KEYS.get(provider, "")

    if provider == "anthropic":
        return AnthropicProvider(api_key, model)
    if provider == "openai":
        return OpenAIProvider(api_key, model)
    if provider == "google":
        return GoogleProvider(api_key, model)
    raise ValueError(f"Unknown LLM provider: {provider}")
