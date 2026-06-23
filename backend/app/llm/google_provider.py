"""Google Gemini provider — streaming text generation.

Tool calling for Gemini is intentionally simplified (text-only round-trips);
the platform routes tool-heavy workloads through Anthropic/OpenAI by default.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.llm.base import (
    ChunkType,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    StreamChunk,
    ToolSpec,
)


class GoogleProvider(LLMProvider):
    name = "google"

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        super().__init__(api_key, model)
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai

    def _build(self, messages: list[LLMMessage], system: str | None):
        history = []
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            history.append({"role": role, "parts": [m.content]})
        model = self._genai.GenerativeModel(
            self.model, system_instruction=system or None
        )
        return model, history

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> LLMResponse:
        model, history = self._build(messages, system)
        resp = await model.generate_content_async(
            history, generation_config={"max_output_tokens": max_tokens}
        )
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            content=resp.text or "",
            model=self.model,
            provider=self.name,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) if usage else 0,
            completion_tokens=getattr(usage, "candidates_token_count", 0) if usage else 0,
            finish_reason="stop",
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        model, history = self._build(messages, system)
        resp = await model.generate_content_async(
            history, generation_config={"max_output_tokens": max_tokens}, stream=True
        )
        async for chunk in resp:
            if getattr(chunk, "text", None):
                yield StreamChunk(ChunkType.TEXT, text=chunk.text)
        yield StreamChunk(ChunkType.DONE)
