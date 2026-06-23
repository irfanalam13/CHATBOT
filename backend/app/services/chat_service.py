"""Chat orchestration — the heart of the platform.

Flow per message:
  validate/guard input → load/create session → persist user msg → build memory
  context → (optional) RAG retrieval + citations → build prompt → stream LLM
  with a tool-calling loop → filter output → persist assistant msg, citations,
  token usage and analytics.
"""
from __future__ import annotations

import time
import uuid
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, ValidationAppError
from app.core.logging import get_logger
from app.llm.base import ChunkType, LLMMessage, ToolCall
from app.llm.factory import get_llm_provider
from app.llm.pricing import estimate_cost
from app.models.chat import (
    ChatSession,
    Message,
    MessageCitation,
    MessageRole,
    SessionStatus,
)
from app.models.tenant import Tenant
from app.repositories.repos import (
    MessageRepo,
    SessionRepo,
    get_tenant_settings,
)
from app.rag.retrieval import RetrievalResult, Retriever
from app.schemas.chat import ChatRequest
from app.security.guards import (
    check_prompt_injection,
    filter_output,
    validate_input,
)
from app.services.analytics_service import AnalyticsService
from app.services.memory_service import MemoryService
from app.services.prompt_builder import build_system_prompt
from app.services.tool_service import ToolService

log = get_logger("services.chat")

MAX_TOOL_ITERATIONS = 5


class ChatService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.sessions = SessionRepo(session, tenant_id)
        self.messages = MessageRepo(session, tenant_id)
        self.memory = MemoryService(session, tenant_id)
        self.analytics = AnalyticsService(session, tenant_id)
        self.tools = ToolService(session, tenant_id)

    async def get_or_create_session(self, req: ChatRequest) -> ChatSession:
        if req.session_id:
            chat = await self.sessions.get_or_404(req.session_id)
            if chat.user_id != self.user_id:
                raise ForbiddenError("Session belongs to another user")
            return chat
        chat = ChatSession(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            knowledge_base_id=req.knowledge_base_id,
            title=req.message[:60],
        )
        return await self.sessions.add(chat)

    async def stream_chat(self, req: ChatRequest) -> AsyncIterator[dict]:
        """Yields event dicts: {type, ...}. Persists state at the end."""
        guard = validate_input(req.message)
        if not guard.allowed:
            raise ValidationAppError(guard.reason or "invalid input")
        injection = check_prompt_injection(req.message)
        if not injection.allowed:
            await self.analytics.record("prompt_injection_blocked", user_id=self.user_id)
            raise ForbiddenError("Request blocked by safety filter")

        chat = await self.get_or_create_session(req)
        yield {"type": "session", "session_id": str(chat.id), "title": chat.title}

        # Persist user message.
        user_msg = await self.messages.add(
            Message(
                tenant_id=self.tenant_id, session_id=chat.id,
                role=MessageRole.USER, content=req.message,
            )
        )
        chat.message_count += 1

        tenant = await self.session.get(Tenant, self.tenant_id)
        ts = await get_tenant_settings(self.session, self.tenant_id)
        provider = get_llm_provider(ts)

        # ── Retrieval / grounding ──────────────────────────────
        retrieval: RetrievalResult | None = None
        context_str = None
        if req.use_rag:
            # Grounding is best-effort: a missing vector store, unconfigured
            # embedding key, or empty knowledge base must not abort the chat.
            # When there is no usable context we fall through silently and let
            # the LLM answer on its own; only genuine context augments the reply.
            try:
                retrieval = await self._retrieve(req, chat, tenant, ts)
            except Exception as e:
                log.warning("rag_retrieval_failed", error=str(e))
                retrieval = None
            if retrieval and retrieval.chunks:
                context_str = retrieval.to_context()
                yield {
                    "type": "citations",
                    "citations": [
                        {
                            "index": i + 1,
                            "document_name": c.document_name,
                            "page_number": c.page_number,
                            "confidence": round(c.score, 4),
                            "source_link": c.source_link,
                            "snippet": c.content[:280],
                        }
                        for i, c in enumerate(retrieval.chunks)
                    ],
                }

        # ── Tools ──────────────────────────────────────────────
        tool_specs, registry = ([], {})
        tools_enabled = req.use_tools and (ts.enable_tools if ts else True)
        if tools_enabled:
            tool_specs, registry = await self.tools.list_specs()

        # ── Build prompt + history ─────────────────────────────
        system_prompt = build_system_prompt(
            tenant_prompt=(ts.system_prompt if ts else None),
            context=context_str,
            has_tools=bool(tool_specs),
        )
        history = await self.memory.build_context(chat, self.user_id)
        history.append(LLMMessage(role="user", content=req.message))

        # ── Stream with tool loop ──────────────────────────────
        started = time.perf_counter()
        full_answer = ""
        prompt_tokens = completion_tokens = 0
        finish_reason = None
        model_used = provider.model

        for iteration in range(MAX_TOOL_ITERATIONS):
            collected = ""
            tool_calls: list[ToolCall] = []
            async for chunk in provider.stream(
                history,
                system=system_prompt,
                tools=tool_specs or None,
                max_tokens=4096,
            ):
                if chunk.type == ChunkType.TEXT:
                    collected += chunk.text
                    yield {"type": "token", "text": chunk.text}
                elif chunk.type == ChunkType.TOOL_USE and chunk.tool_call:
                    tool_calls.append(chunk.tool_call)
                elif chunk.type == ChunkType.DONE:
                    prompt_tokens += chunk.prompt_tokens
                    completion_tokens += chunk.completion_tokens
                    finish_reason = chunk.finish_reason
                    if chunk.model:
                        model_used = chunk.model

            full_answer += collected
            if not tool_calls:
                break

            history.append(
                LLMMessage(
                    role="assistant",
                    content=collected,
                    tool_calls=[
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in tool_calls
                    ],
                )
            )
            for tc in tool_calls:
                yield {"type": "tool_call", "name": tc.name, "arguments": tc.arguments}
                result = await self.tools.execute(tc, registry)
                yield {"type": "tool_result", "name": tc.name}
                history.append(
                    LLMMessage(role="tool", content=result, tool_call_id=tc.id)
                )

        # ── Output filtering ───────────────────────────────────
        clean_answer, leaks = filter_output(full_answer)
        if leaks:
            log.warning("output_leak_redacted", findings=leaks)
            yield {"type": "warning", "message": "Sensitive content was redacted."}

        latency_ms = int((time.perf_counter() - started) * 1000)

        # ── Persist assistant message + citations + usage ──────
        assistant_msg = await self.messages.add(
            Message(
                tenant_id=self.tenant_id, session_id=chat.id, role=MessageRole.ASSISTANT,
                content=clean_answer, parent_id=user_msg.id, model=model_used,
                provider=provider.name, prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens, latency_ms=latency_ms,
                finish_reason=finish_reason,
            )
        )
        chat.message_count += 1
        if retrieval:
            await self._persist_citations(assistant_msg.id, retrieval)

        await self.analytics.record_usage(
            user_id=self.user_id, message_id=assistant_msg.id, provider=provider.name,
            model=model_used, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, latency_ms=latency_ms,
        )
        await self.analytics.record(
            "question_asked", user_id=self.user_id, session_id=chat.id,
            payload={"length": len(req.message), "used_rag": bool(context_str)},
        )
        if req.use_rag and retrieval is not None and not retrieval.chunks:
            await self.analytics.record(
                "search_failed", user_id=self.user_id, payload={"query": req.message[:200]}
            )

        await self.memory.maybe_summarize(chat, provider)

        yield {
            "type": "done",
            "message_id": str(assistant_msg.id),
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost_usd": round(estimate_cost(model_used, prompt_tokens, completion_tokens), 6),
            },
            "latency_ms": latency_ms,
        }

    # ── helpers ───────────────────────────────────────────────
    async def _retrieve(self, req, chat, tenant, ts) -> RetrievalResult:
        from app.services.ingestion_service import _tenant_embedding_keys

        retriever = Retriever(
            ts.embedding_provider if ts else None,
            ts.embedding_model if ts else None,
            api_keys=_tenant_embedding_keys(ts),
        )
        filters = {}
        kb = req.knowledge_base_id or chat.knowledge_base_id
        if kb:
            filters["knowledge_base_id"] = str(kb)
        return await retriever.retrieve(
            collection=tenant.vector_collection,
            tenant_id=str(self.tenant_id),
            query=req.message,
            mode="hybrid",
            top_k=(ts.retrieval_top_k if ts and ts.retrieval_top_k else settings.RETRIEVAL_TOP_K),
            rerank_enabled=(ts.enable_reranking if ts else None),
            filters=filters,
        )

    async def _persist_citations(self, message_id: uuid.UUID, retrieval: RetrievalResult) -> None:
        for c in retrieval.chunks:
            self.session.add(
                MessageCitation(
                    tenant_id=self.tenant_id,
                    message_id=message_id,
                    document_id=uuid.UUID(c.document_id) if c.document_id else None,
                    chunk_id=uuid.UUID(c.chunk_id) if c.chunk_id else None,
                    document_name=c.document_name,
                    chunk_reference=f"chunk:{c.chunk_id}" if c.chunk_id else None,
                    page_number=c.page_number,
                    confidence=c.score,
                    source_link=c.source_link,
                    snippet=c.content[:500],
                )
            )
        await self.session.flush()
