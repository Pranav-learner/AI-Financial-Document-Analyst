"""Celery tasks for Advanced Retrieval & RAG (Phase 6)."""

from __future__ import annotations

import asyncio
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.retrieval.evaluation.evaluation_service import EvaluationService
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="app.tasks.rag.run_async_evaluation", acks_late=True)
def run_async_evaluation(retrieval_type: str = "both", top_k: int | None = None) -> dict:
    """Asynchronously run retrieval evaluations over the benchmark suite."""
    log.info("tasks.rag.run_async_evaluation.start", retrieval_type=retrieval_type, top_k=top_k)

    async def _run():
        async with AsyncSessionLocal() as session:
            service = EvaluationService(session)
            runs = await service.run(retrieval_type=retrieval_type, top_k=top_k)
            return [r.summary() for r in runs]

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        runs_summary = loop.run_until_complete(_run())
        log.info("tasks.rag.run_async_evaluation.success", count=len(runs_summary))
        return {"status": "SUCCESS", "runs": runs_summary}
    except Exception as exc:
        log.exception("tasks.rag.run_async_evaluation.failed", error=str(exc))
        return {"status": "FAILED", "error": str(exc)}
