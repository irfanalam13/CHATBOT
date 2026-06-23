"""OpenAI provider (GPT family) — Chat Completions with tools + streaming."""
from __future__ import annotations

import json
from typing import AsyncIterator

from app.llm.base import (
    ChunkType,
    LLMMessage,
    LLMProvider,
    LLMResponse,
    StreamChunk,
    ToolCall,
    ToolSpec,
)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        super().__init__(api_key, model)
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key)

    def _to_messages(self, messages: list[LLMMessage], system: str | None) -> list[dict]:
        out: list[dict] = []
        if system:
            out.append({"role": "system", "content": system})
        for m in messages:
            if m.role == "tool":
                out.append(
                    {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
                )
            elif m.role == "assistant" and m.tool_calls:
                out.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc.get("arguments", {})),
                                },
                            }
                            for tc in m.tool_calls
                        ],
                    }
                )
            else:
                out.append({"role": m.role, "content": m.content})
        return out

    def _tools_param(self, tools: list[ToolSpec] | None) -> list[dict] | None:
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self.model,
            "messages": self._to_messages(messages, system),
            "max_tokens": max_tokens,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        tp = self._tools_param(tools)
        if tp:
            kwargs["tools"] = tp
        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments or "{}"))
            for tc in (choice.message.tool_calls or [])
        ]
        return LLMResponse(
            content=choice.message.content or "",
            model=resp.model,
            provider=self.name,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
            finish_reason=choice.finish_reason,
            tool_calls=tool_calls,
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
        kwargs: dict = {
            "model": self.model,
            "messages": self._to_messages(messages, system),
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        tp = self._tools_param(tools)
        if tp:
            kwargs["tools"] = tp

        tool_buffer: dict[int, dict] = {}
        prompt_tokens = completion_tokens = 0
        finish_reason = None
        async for chunk in await self._client.chat.completions.create(**kwargs):
            if chunk.usage:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta
            if delta.content:
                yield StreamChunk(ChunkType.TEXT, text=delta.content)
            for tc in delta.tool_calls or []:
                buf = tool_buffer.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                if tc.id:
                    buf["id"] = tc.id
                if tc.function and tc.function.name:
                    buf["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    buf["args"] += tc.function.arguments

        for buf in tool_buffer.values():
            try:
                args = json.loads(buf["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            yield StreamChunk(
                ChunkType.TOOL_USE,
                tool_call=ToolCall(id=buf["id"], name=buf["name"], arguments=args),
            )
        yield StreamChunk(
            ChunkType.DONE,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
            model=self.model,
        )
