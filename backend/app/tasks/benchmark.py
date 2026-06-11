"""Celery tasks for Competitor Benchmarking (Phase 8)."""

from __future__ import annotations

import asyncio
import uuid

from app.benchmarking.benchmark_service import BenchmarkService
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.tasks.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="app.tasks.benchmark.run_benchmark_task", acks_late=True)
def run_benchmark_task(run_id_str: str) -> dict:
    """Asynchronously execute a benchmark run."""
    run_id = uuid.UUID(run_id_str)
    log.info("tasks.benchmark.run_benchmark_task.start", run_id=run_id)

    async def _run():
        async with AsyncSessionLocal() as session:
            service = BenchmarkService(session)
            await service.run_benchmark(run_id)
            return {"run_id": str(run_id), "status": "COMPLETED"}

    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(_run())
        log.info("tasks.benchmark.run_benchmark_task.success", run_id=run_id)
        return result
    except Exception as exc:
        log.exception("tasks.benchmark.run_benchmark_task.failed", run_id=run_id, error=str(exc))
        return {"run_id": str(run_id), "status": "FAILED", "error": str(exc)}
