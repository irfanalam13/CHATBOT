"""Chat: sessions CRUD + streaming (SSE & WebSocket) + message operations."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, get_principal, require_permission
from app.core.database import AsyncSessionLocal, get_db
from app.core.exceptions import AuthError, ForbiddenError
from app.core.rbac import Permission
from app.core.security import ACCESS_TOKEN, decode_token
from app.models.chat import ChatSession, Message, SessionStatus
from app.repositories.repos import MessageRepo, SessionRepo
from app.schemas.chat import (
    ChatRequest,
    EditMessageRequest,
    MessageOut,
    ReactionRequest,
    SessionCreate,
    SessionOut,
    SessionUpdate,
)
from app.schemas.common import MessageResponse, Page
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Streaming completion (SSE) ─────────────────────────────────
@router.post("/completions")
async def chat_completions(
    body: ChatRequest,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
):
    if principal.user_id is None:
        raise ForbiddenError("API keys cannot start interactive chats")

    async def event_stream():
        # Use a dedicated session so the generator owns its own transaction.
        async with AsyncSessionLocal() as db:
            service = ChatService(db, principal.tenant_id, principal.user_id)
            try:
                async for event in service.stream_chat(body):
                    yield f"data: {json.dumps(event)}\n\n"
                await db.commit()
            except Exception as e:  # surface the error to the client cleanly
                await db.rollback()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Streaming completion (WebSocket) ───────────────────────────
@router.websocket("/ws")
async def chat_ws(websocket: WebSocket, token: str = Query(...)):
    await websocket.accept()
    try:
        payload = decode_token(token)
        if payload.get("type") != ACCESS_TOKEN:
            raise AuthError("bad token")
        tenant_id = uuid.UUID(payload["tenant_id"])
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        await websocket.close(code=4401)
        return

    try:
        while True:
            raw = await websocket.receive_text()
            body = ChatRequest(**json.loads(raw))
            async with AsyncSessionLocal() as db:
                service = ChatService(db, tenant_id, user_id)
                try:
                    async for event in service.stream_chat(body):
                        await websocket.send_text(json.dumps(event))
                    await db.commit()
                except Exception as e:
                    await db.rollback()
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
    except WebSocketDisconnect:
        return


# ── Sessions ───────────────────────────────────────────────────
@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_session(
    body: SessionCreate,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    repo = SessionRepo(db, principal.tenant_id)
    chat = ChatSession(
        tenant_id=principal.tenant_id, user_id=principal.user_id,
        knowledge_base_id=body.knowledge_base_id,
        title=body.title or "New chat", category=body.category, metadata_=body.metadata,
    )
    await repo.add(chat)
    return SessionOut.model_validate(chat)


@router.get("/sessions", response_model=Page[SessionOut])
async def list_sessions(
    page: int = 1, page_size: int = 20, category: str | None = None,
    pinned: bool | None = None, status: str | None = None, q: str | None = None,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> Page[SessionOut]:
    repo = SessionRepo(db, principal.tenant_id)
    filters = [ChatSession.user_id == principal.user_id]
    if category:
        filters.append(ChatSession.category == category)
    if pinned is not None:
        filters.append(ChatSession.pinned.is_(pinned))
    if status:
        filters.append(ChatSession.status == SessionStatus(status))
    else:
        filters.append(ChatSession.status != SessionStatus.DELETED)
    if q:
        filters.append(ChatSession.title.ilike(f"%{q}%"))
    rows, total = await repo.list(
        offset=(page - 1) * page_size, limit=page_size, filters=filters,
        order_by=ChatSession.pinned.desc(),
    )
    return Page(items=[SessionOut.model_validate(r) for r in rows], total=total,
                page=page, page_size=page_size)


@router.get("/sessions/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    chat = await _owned_session(db, principal, session_id)
    return SessionOut.model_validate(chat)


@router.patch("/sessions/{session_id}", response_model=SessionOut)
async def update_session(
    session_id: uuid.UUID, body: SessionUpdate,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    chat = await _owned_session(db, principal, session_id)
    if body.title is not None:
        chat.title = body.title
    if body.category is not None:
        chat.category = body.category
    if body.pinned is not None:
        chat.pinned = body.pinned
    if body.status is not None:
        chat.status = SessionStatus(body.status)
    await db.flush()
    return SessionOut.model_validate(chat)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def delete_session(
    session_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    chat = await _owned_session(db, principal, session_id)
    chat.status = SessionStatus.DELETED  # soft delete
    await db.flush()
    return MessageResponse(message="Session deleted")


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def session_messages(
    session_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    await _owned_session(db, principal, session_id)
    repo = MessageRepo(db, principal.tenant_id)
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select

    stmt = (
        select(Message)
        .where(Message.tenant_id == principal.tenant_id, Message.session_id == session_id)
        .options(selectinload(Message.citations))
        .order_by(Message.created_at.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [MessageOut.model_validate(m) for m in rows]


# ── Message operations ─────────────────────────────────────────
@router.post("/messages/{message_id}/reaction", response_model=MessageResponse)
async def react(
    message_id: uuid.UUID, body: ReactionRequest,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = MessageRepo(db, principal.tenant_id)
    msg = await repo.get_or_404(message_id)
    msg.reaction = body.reaction
    await db.flush()
    return MessageResponse(message="Reaction saved")


@router.patch("/messages/{message_id}", response_model=MessageResponse)
async def edit_message(
    message_id: uuid.UUID, body: EditMessageRequest,
    principal: Principal = Depends(require_permission(Permission.CHAT_USE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    repo = MessageRepo(db, principal.tenant_id)
    msg = await repo.get_or_404(message_id)
    msg.content = body.content
    msg.is_edited = True
    await db.flush()
    return MessageResponse(message="Message updated")


# ── helpers ────────────────────────────────────────────────────
async def _owned_session(db, principal: Principal, session_id: uuid.UUID) -> ChatSession:
    repo = SessionRepo(db, principal.tenant_id)
    chat = await repo.get_or_404(session_id)
    if chat.user_id != principal.user_id:
        # Managers/admins may read all sessions in their tenant.
        from app.core.rbac import has_permission

        if not has_permission(principal.role, Permission.CHAT_READ_ALL, set(principal.scopes)):
            raise ForbiddenError("Not your session")
    return chat
