"""RAG pipeline diagnostic endpoint.

GET /api/v1/rag/pipeline-status/{report_id}

Returns a full pipeline health report:
- chunk count, embedded count, unembedded count
- sample chunk text (first 200 chars)
- mini retrieval smoke test (top-1 vector search)
- metadata about the report's processing stage

Use this to verify the entire Upload → Chunk → Embed → Retrieve path
is working end-to-end before running Analyst Chat.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document_chunk import DocumentChunk
from app.models.report import Report
from app.retrieval.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.retrieval.hybrid import HybridRetrievalService, RetrievalContext
from app.retrieval.search.query_embedding import QueryEmbedder

router = APIRouter()


@router.get(
    "/pipeline-status/{report_id}",
    summary="Verify the RAG pipeline health for a specific report",
)
async def pipeline_status(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """End-to-end RAG pipeline health check for a single report.

    Returns chunk counts, embedding coverage, and a live retrieval smoke-test
    so you can pinpoint exactly where the pipeline breaks.
    """
    # ── 1. Report existence ──────────────────────────────────────────────────
    report: Report | None = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found.",
        )

    # ── 2. Chunk counts ──────────────────────────────────────────────────────
    total_chunks: int = int(
        (await db.scalar(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.report_id == report_id)
        )) or 0
    )
    embedded_chunks: int = int(
        (await db.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.report_id == report_id,
                DocumentChunk.embedding.is_not(None),
            )
        )) or 0
    )
    unembedded_chunks = total_chunks - embedded_chunks

    # ── 3. Sample chunk (first one, any embedding status) ───────────────────
    sample_row = (
        await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.report_id == report_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(1)
        )
    ).scalars().first()

    sample_chunk = None
    if sample_row:
        sample_chunk = {
            "id": str(sample_row.id),
            "chunk_index": sample_row.chunk_index,
            "has_embedding": sample_row.embedding is not None,
            "text_preview": (sample_row.chunk_text or "")[:300],
            "metadata": sample_row.chunk_metadata,
        }

    # ── 4. Live retrieval smoke-test ─────────────────────────────────────────
    retrieval_result: dict[str, Any] = {"status": "skipped", "reason": "no embedded chunks"}
    if embedded_chunks > 0:
        try:
            provider = GeminiEmbeddingProvider.from_settings()
            embedder = QueryEmbedder(provider)
            svc = HybridRetrievalService(db, query_embedder=embedder)
            ctx = RetrievalContext(report_id=report_id)
            outcome = await svc.run(
                query="What are the key financial metrics and net sales?",
                context=ctx,
                top_k=3,
                profile="GENERAL",
            )
            retrieval_result = {
                "status": "ok",
                "candidate_count": outcome.candidate_count,
                "returned_count": len(outcome.results),
                "top_score": outcome.results[0].score if outcome.results else None,
                "top_chunk_preview": (outcome.results[0].chunk_text or "")[:200] if outcome.results else None,
                "applied_filters": outcome.applied_filters,
                "timings": outcome.timings.as_dict(),
            }
        except Exception as exc:
            retrieval_result = {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    return {
        "report_id": str(report_id),
        "report_status": report.status,
        "completed_stage": report.completed_stage,
        "failed_stage": report.failed_stage,
        "pipeline_health": {
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_chunks,
            "unembedded_chunks": unembedded_chunks,
            "embedding_coverage_pct": round(
                (embedded_chunks / total_chunks * 100) if total_chunks else 0, 1
            ),
            "chunks_ok": total_chunks > 0,
            "embeddings_ok": embedded_chunks > 0,
            "retrieval_ready": embedded_chunks > 0,
        },
        "sample_chunk": sample_chunk,
        "retrieval_smoke_test": retrieval_result,
    }
