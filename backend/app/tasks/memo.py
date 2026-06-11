"""Celery tasks for Investment Memo Generation Engine (Phase 9)."""

from __future__ import annotations

import uuid
from app.core.logging import get_logger
from app.db.session import SyncSessionLocal
from app.memo.memo_orchestrator import MemoOrchestrator
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="app.tasks.memo.generate_memo_task", acks_late=True)
def generate_memo_task(memo_id_str: str) -> dict:
    """Asynchronously execute investment memo generation."""
    memo_id = uuid.UUID(memo_id_str)
    log.info("tasks.memo.generate_memo_task.start", memo_id=memo_id)

    with SyncSessionLocal() as session:
        try:
            orchestrator = MemoOrchestrator(session)
            orchestrator.generate_memo_sync(memo_id)
            log.info("tasks.memo.generate_memo_task.success", memo_id=memo_id)
            return {"memo_id": str(memo_id), "status": "COMPLETED"}
        except Exception as exc:
            log.exception("tasks.memo.generate_memo_task.failed", memo_id=memo_id, error=str(exc))
            return {"memo_id": str(memo_id), "status": "FAILED", "error": str(exc)}
