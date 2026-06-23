"""Conversation memory: short-term window, rolling summaries, and long-term
memories at session / user / tenant scope, with context-window optimisation."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.llm.base import LLMMessage, LLMProvider
from app.models.chat import ChatSession, Memory, MemoryScope, Message, MessageRole
from app.repositories.repos import MemoryRepo, MessageRepo

log = get_logger("services.memory")

# How many recent messages to keep verbatim before relying on the summary.
SHORT_TERM_WINDOW = 12
# Summarise once the transcript exceeds this many messages.
SUMMARY_TRIGGER = 20


class MemoryService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.memories = MemoryRepo(session, tenant_id)
        self.messages = MessageRepo(session, tenant_id)

    async def build_context(
        self, chat: ChatSession, user_id: uuid.UUID
    ) -> list[LLMMessage]:
        """Assemble the message list sent to the LLM: summary + recent window +
        relevant long-term memories."""
        recent = await self.messages.recent_for_session(chat.id, SHORT_TERM_WINDOW)

        context: list[LLMMessage] = []

        # Long-term memory injected as a system-style preamble (user turn).
        memory_block = await self._relevant_memories(chat.id, user_id)
        preamble_parts = []
        if chat.summary:
            preamble_parts.append(f"Conversation summary so far:\n{chat.summary}")
        if memory_block:
            preamble_parts.append("Relevant remembered facts:\n" + memory_block)
        if preamble_parts:
            context.append(LLMMessage(role="user", content="\n\n".join(preamble_parts)))
            context.append(LLMMessage(role="assistant", content="Understood. I'll keep that in mind."))

        for m in recent:
            role = "assistant" if m.role == MessageRole.ASSISTANT else "user"
            if m.role in (MessageRole.USER, MessageRole.ASSISTANT) and m.content:
                context.append(LLMMessage(role=role, content=m.content))
        return context

    async def _relevant_memories(self, session_id: uuid.UUID, user_id: uuid.UUID) -> str:
        rows = await self.memories.relevant(
            user_id=user_id, session_id=session_id, limit=10
        )
        return "\n".join(f"- {m.content}" for m in rows)

    async def remember(
        self, *, scope: MemoryScope, owner_id: uuid.UUID | None, content: str,
        importance: float = 0.5, key: str | None = None,
    ) -> Memory:
        mem = Memory(
            tenant_id=self.tenant_id, scope=scope, owner_id=owner_id,
            content=content, importance=importance, key=key,
        )
        return await self.memories.add(mem)

    async def maybe_summarize(self, chat: ChatSession, llm: LLMProvider) -> None:
        """Compress older turns into a rolling summary (context-window optimisation)."""
        if chat.message_count < SUMMARY_TRIGGER:
            return
        history = await self.messages.for_session(chat.id)
        older = history[:-SHORT_TERM_WINDOW]
        if not older:
            return
        transcript = "\n".join(
            f"{m.role.value}: {m.content}" for m in older if m.content
        )[:16000]
        prompt = (
            "Summarise the following conversation concisely, preserving facts, "
            "decisions, names, and open questions. Keep it under 200 words.\n\n"
            f"{transcript}"
        )
        try:
            resp = await llm.generate(
                [LLMMessage(role="user", content=prompt)], max_tokens=512
            )
            chat.summary = resp.content
        except Exception as e:  # pragma: no cover
            log.warning("summarize_failed", error=str(e))
