"""Celery tasks. Async service code is bridged via asyncio.run."""
from __future__ import annotations

import asyncio

from app.core.logging import get_logger
from app.workers.celery_app import celery_app

log = get_logger("workers.tasks")


def _run(coro):
    return asyncio.run(coro)


@celery_app.task(name="app.workers.tasks.ingest_document", bind=True, max_retries=3)
def ingest_document(self, document_id: str) -> dict:
    from app.services.ingestion_service import process_document

    try:
        _run(process_document(document_id))
        return {"document_id": document_id, "status": "processed"}
    except Exception as exc:  # pragma: no cover
        log.exception("ingest_task_failed", document_id=document_id)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="app.workers.tasks.reprocess_document")
def reprocess_document(document_id: str) -> dict:
    from app.services.ingestion_service import process_document

    _run(process_document(document_id))
    return {"document_id": document_id, "status": "reprocessed"}


@celery_app.task(name="app.workers.tasks.run_retraining")
def run_retraining(tenant_id: str) -> dict:
    """Retraining pipeline hook — re-embeds corrected answers from the review
    queue into a curated knowledge base. Stubbed for wiring."""
    log.info("retraining_triggered", tenant_id=tenant_id)
    return {"tenant_id": tenant_id, "status": "queued"}
