"""Anthropic provider — Claude (default: claude-opus-4-8).

Follows the Anthropic Python SDK guidance:
  * adaptive thinking for non-tool turns (`thinking={"type": "adaptive"}`)
  * `client.messages.stream()` for token streaming
  * the standard tool-use loop (caller drives execution; see ChatService)
  * NO sampling params on Opus 4.7/4.8 / Fable / Sonnet 4.6 (they 400)
"""
from __future__ import annotations

from typing import AsyncIterator

from app.core.logging import get_logger
from app.llm.base import (
    ChunkType,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    StreamChunk,
    ToolCall,
    ToolSpec,
)

log = get_logger("llm.anthropic")

# Models that reject temperature/top_p/top_k and budget_tokens.
_ADAPTIVE_THINKING_MODELS = ("claude-opus-4", "claude-sonnet-4-6", "claude-fable", "claude-haiku-4-5")


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        super().__init__(api_key, model)
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ── conversion helpers ─────────────────────────────────────
    def _to_anthropic_messages(self, messages: list[LLMMessage]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            if m.role == "system":
                continue
            if m.role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id,
                                "content": m.content,
                            }
                        ],
                    }
                )
            elif m.role == "assistant" and m.tool_calls:
                blocks: list[dict] = []
                if m.content:
                    blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc.get("arguments", {}),
                        }
                    )
                out.append({"role": "assistant", "content": blocks})
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    def _tools_param(self, tools: list[ToolSpec] | None) -> list[dict] | None:
        if not tools:
            return None
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]

    def _supports_adaptive_thinking(self) -> bool:
        return any(self.model.startswith(p) for p in _ADAPTIVE_THINKING_MODELS)

    def _common_kwargs(self, system, tools, max_tokens, *, enable_thinking: bool) -> dict:
        kwargs: dict = {"model": self.model, "max_tokens": max_tokens}
        if system:
            kwargs["system"] = system
        tp = self._tools_param(tools)
        if tp:
            kwargs["tools"] = tp
        # Thinking only when no tools (keeps the tool loop free of thinking-block echo rules).
        if enable_thinking and not tp and self._supports_adaptive_thinking():
            kwargs["thinking"] = {"type": "adaptive"}
        return kwargs

    # ── generate (non-streaming, used for tool loops & summaries) ─
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,  # ignored on modern Claude models
    ) -> LLMResponse:
        kwargs = self._common_kwargs(system, tools, max_tokens, enable_thinking=False)
        resp = await self._client.messages.create(
            messages=self._to_anthropic_messages(messages), **kwargs
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )

        return LLMResponse(
            content="".join(text_parts),
            model=resp.model,
            provider=self.name,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            finish_reason=resp.stop_reason,
            tool_calls=tool_calls,
        )

    # ── streaming ──────────────────────────────────────────────
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        kwargs = self._common_kwargs(system, tools, max_tokens, enable_thinking=True)
        async with self._client.messages.stream(
            messages=self._to_anthropic_messages(messages), **kwargs
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield StreamChunk(ChunkType.TEXT, text=event.delta.text)
                    elif event.delta.type == "thinking_delta":
                        yield StreamChunk(ChunkType.THINKING, text=event.delta.thinking)

            final = await stream.get_final_message()
            for block in final.content:
                if block.type == "tool_use":
                    yield StreamChunk(
                        ChunkType.TOOL_USE,
                        tool_call=ToolCall(
                            id=block.id, name=block.name, arguments=dict(block.input)
                        ),
                    )
        yield StreamChunk(
            ChunkType.DONE,
            prompt_tokens=final.usage.input_tokens,
            completion_tokens=final.usage.output_tokens,
            finish_reason=final.stop_reason,
            model=final.model,
        )
