"""RAG endpoints (Phase 6). Mounted at /api/v1/rag."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.rag.service import AdvancedRAGService
from app.retrieval.hybrid import RetrievalContext
from app.schemas.rag import (
    RAGDebugResponse,
    RAGRetrieveRequest,
    RAGRetrieveResponse,
    CitationOut,
)

router = APIRouter()


def get_rag_service(db: AsyncSession = Depends(get_db)) -> AdvancedRAGService:
    """Injectable helper to provide AdvancedRAGService."""
    return AdvancedRAGService(db)


def _context(payload: RAGRetrieveRequest) -> RetrievalContext:
    f = payload.filters
    return RetrievalContext(
        company_id=f.company_id,
        report_id=f.report_id,
        year=f.year,
        quarter=f.quarter,
        report_type=f.report_type,
        section_name=f.section_name,
        normalized_section_name=f.normalized_section_name,
    )


@router.post(
    "/retrieve",
    response_model=RAGRetrieveResponse,
    summary="Advanced RAG retrieval: Query rewriting, HyDE, Multi-Query, Rerank, and Context Assembly",
)
async def retrieve_context(
    payload: RAGRetrieveRequest,
    service: AdvancedRAGService = Depends(get_rag_service),
) -> RAGRetrieveResponse:
    context_pkg, _, _, _ = await service.retrieve_and_assemble(
        query=payload.query,
        context=_context(payload),
        strategy=payload.strategy,
        top_k=payload.top_k,
    )
    return RAGRetrieveResponse(
        context_text=context_pkg.context_text,
        tokens_used=context_pkg.tokens_used,
        budget_limit=context_pkg.budget_limit,
        citations=[
            CitationOut(
                citation_id=c.citation_id,
                report_id=c.report_id,
                chunk_id=c.chunk_id,
                page_number=c.page_number,
                section_name=c.section_name,
                source_text_preview=c.source_text_preview,
            )
            for c in context_pkg.citations
        ],
    )


@router.post(
    "/debug",
    response_model=RAGDebugResponse,
    summary="Advanced RAG diagnostics: Query rewriting, HyDE, Multi-Query, Rerank, and Context Assembly trace",
)
async def debug_retrieve_context(
    payload: RAGRetrieveRequest,
    service: AdvancedRAGService = Depends(get_rag_service),
) -> RAGDebugResponse:
    context_pkg, steps, _, _ = await service.retrieve_and_assemble(
        query=payload.query,
        context=_context(payload),
        strategy=payload.strategy,
        top_k=payload.top_k,
    )
    return RAGDebugResponse(
        query=payload.query,
        strategy=steps.get("resolved_strategy", "GENERAL_ANALYSIS"),
        steps=steps,
        context_text=context_pkg.context_text,
        tokens_used=context_pkg.tokens_used,
        budget_limit=context_pkg.budget_limit,
        citations=[
            CitationOut(
                citation_id=c.citation_id,
                report_id=c.report_id,
                chunk_id=c.chunk_id,
                page_number=c.page_number,
                section_name=c.section_name,
                source_text_preview=c.source_text_preview,
            )
            for c in context_pkg.citations
        ],
    )
