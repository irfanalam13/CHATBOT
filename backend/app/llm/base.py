"""Provider-agnostic LLM abstraction shared by Anthropic / OpenAI / Gemini."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator


class ChunkType(str, Enum):
    TEXT = "text"
    THINKING = "thinking"
    TOOL_USE = "tool_use"
    DONE = "done"


@dataclass
class LLMMessage:
    role: str                      # user | assistant | system | tool
    content: str
    # For tool result / tool call round-trips (provider-normalised).
    tool_call_id: str | None = None
    name: str | None = None
    tool_calls: list[dict] = field(default_factory=list)


@dataclass
class ToolSpec:
    """Normalised tool definition; each provider renders it to its own shape."""
    name: str
    description: str
    input_schema: dict


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class StreamChunk:
    type: ChunkType
    text: str = ""
    tool_call: ToolCall | None = None
    # Populated on the terminal DONE chunk.
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    model: str | None = None


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(abc.ABC):
    """Interface every concrete provider implements."""

    name: str = "base"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abc.abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Single, non-streaming completion (used for tool loops & summaries)."""

    @abc.abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        tools: list[ToolSpec] | None = None,
        max_tokens: int = 4096,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Token-by-token streaming completion."""
        raise NotImplementedError
        yield  # pragma: no cover  (makes this an async generator)
