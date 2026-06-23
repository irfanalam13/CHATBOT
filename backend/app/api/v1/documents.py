"""Document upload + ingestion lifecycle endpoints."""
from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, require_permission
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, ValidationAppError
from app.core.rbac import Permission
from app.models.document import Document, DocumentStatus
from app.repositories.repos import ChunkRepo, DocumentRepo, KnowledgeBaseRepo
from app.schemas.common import MessageResponse, Page
from app.schemas.document import DocumentChunkOut, DocumentOut, IngestTextRequest
from app.services.storage import get_storage
from app.workers.tasks import ingest_document, reprocess_document

router = APIRouter(prefix="/documents", tags=["documents"])


def _file_type(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload(
    knowledge_base_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    principal: Principal = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    ext = "." + _file_type(file.filename or "")
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationAppError(f"Unsupported file type: {ext}")

    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationAppError("File too large")

    # Validate KB ownership (tenant isolation).
    await KnowledgeBaseRepo(db, principal.tenant_id).get_or_404(knowledge_base_id)

    checksum = hashlib.sha256(data).hexdigest()
    storage_key = f"{principal.tenant_id}/{knowledge_base_id}/{uuid.uuid4()}{ext}"
    storage = get_storage()
    storage.ensure_bucket()
    storage.put(storage_key, data, file.content_type)

    doc = Document(
        tenant_id=principal.tenant_id,
        knowledge_base_id=knowledge_base_id,
        uploaded_by=principal.user_id,
        filename=file.filename or "upload",
        content_type=file.content_type,
        file_type=_file_type(file.filename or ""),
        size_bytes=len(data),
        checksum=checksum,
        storage_key=storage_key,
        status=DocumentStatus.UPLOADED,
    )
    await DocumentRepo(db, principal.tenant_id).add(doc)
    await db.commit()

    ingest_document.delay(str(doc.id))
    return DocumentOut.model_validate(doc)


@router.post("/ingest-text", response_model=DocumentOut, status_code=201)
async def ingest_text(
    body: IngestTextRequest,
    principal: Principal = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    await KnowledgeBaseRepo(db, principal.tenant_id).get_or_404(body.knowledge_base_id)
    data = body.text.encode("utf-8")
    storage_key = f"{principal.tenant_id}/{body.knowledge_base_id}/{uuid.uuid4()}.txt"
    storage = get_storage()
    storage.ensure_bucket()
    storage.put(storage_key, data, "text/plain")

    doc = Document(
        tenant_id=principal.tenant_id, knowledge_base_id=body.knowledge_base_id,
        uploaded_by=principal.user_id, filename=body.filename, file_type="txt",
        content_type="text/plain", size_bytes=len(data),
        checksum=hashlib.sha256(data).hexdigest(), storage_key=storage_key,
        status=DocumentStatus.UPLOADED,
    )
    await DocumentRepo(db, principal.tenant_id).add(doc)
    await db.commit()
    ingest_document.delay(str(doc.id))
    return DocumentOut.model_validate(doc)


@router.get("", response_model=Page[DocumentOut])
async def list_documents(
    page: int = 1, page_size: int = 20, knowledge_base_id: uuid.UUID | None = None,
    status: str | None = None,
    principal: Principal = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
) -> Page[DocumentOut]:
    repo = DocumentRepo(db, principal.tenant_id)
    filters = []
    if knowledge_base_id:
        filters.append(Document.knowledge_base_id == knowledge_base_id)
    if status:
        filters.append(Document.status == DocumentStatus(status))
    rows, total = await repo.list(offset=(page - 1) * page_size, limit=page_size, filters=filters)
    return Page(items=[DocumentOut.model_validate(d) for d in rows], total=total,
                page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    doc = await DocumentRepo(db, principal.tenant_id).get_or_404(document_id)
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/chunks", response_model=Page[DocumentChunkOut])
async def list_chunks(
    document_id: uuid.UUID, page: int = 1, page_size: int = 50,
    principal: Principal = Depends(require_permission(Permission.DOC_READ)),
    db: AsyncSession = Depends(get_db),
) -> Page[DocumentChunkOut]:
    from app.models.document import DocumentChunk

    await DocumentRepo(db, principal.tenant_id).get_or_404(document_id)
    repo = ChunkRepo(db, principal.tenant_id)
    rows, total = await repo.list(
        offset=(page - 1) * page_size, limit=page_size,
        filters=[DocumentChunk.document_id == document_id],
        order_by=DocumentChunk.chunk_index.asc(),
    )
    return Page(items=[DocumentChunkOut.model_validate(c) for c in rows], total=total,
                page=page, page_size=page_size)


@router.post("/{document_id}/reprocess", response_model=MessageResponse)
async def reprocess(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.DOC_UPLOAD)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    doc = await DocumentRepo(db, principal.tenant_id).get_or_404(document_id)
    doc.version += 1
    doc.status = DocumentStatus.UPLOADED
    await db.commit()
    reprocess_document.delay(str(doc.id))
    return MessageResponse(message="Reprocessing queued")


@router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.DOC_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    from app.models.tenant import Tenant
    from app.rag.vectorstore import get_vector_store

    repo = DocumentRepo(db, principal.tenant_id)
    doc = await repo.get_or_404(document_id)
    tenant = await db.get(Tenant, principal.tenant_id)
    try:
        await get_vector_store().delete_document(
            tenant.vector_collection, str(principal.tenant_id), str(document_id)
        )
    except Exception:
        pass
    if doc.storage_key:
        try:
            get_storage().delete(doc.storage_key)
        except Exception:
            pass
    await repo.delete(doc)
    return MessageResponse(message="Document deleted")
