"""Vector search endpoints (Phase 2B). Mounted at /api/v1/search.

Retrieval only: returns semantically relevant chunks + similarity scores. No
answers, no generation, no metadata filtering, no re-ranking.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.retrieval.search import VectorSearchService
from app.retrieval.search.retrieval_models import SearchOutcome, SearchResult
from app.schemas.search import (
    QueryEmbeddingStatsOut,
    SearchDebugResponse,
    SearchRequest,
    SearchResponse,
    SearchResultOut,
    SearchTimingsOut,
)

router = APIRouter()


def get_search_service(db: AsyncSession = Depends(get_db)) -> VectorSearchService:
    """Provide a search service (default: real Gemini query embedder).

    Injectable so tests can supply a deterministic embedder without a live API.
    """
    return VectorSearchService(db)


def _result_out(r: SearchResult) -> SearchResultOut:
    return SearchResultOut(
        chunk_id=r.chunk_id,
        report_id=r.report_id,
        section_id=r.section_id,
        score=r.score,
        chunk_text=r.chunk_text,
        metadata=r.metadata,
    )


def _timings_out(outcome: SearchOutcome) -> SearchTimingsOut:
    return SearchTimingsOut(**outcome.timings.as_dict())


@router.post(
    "/vector",
    response_model=SearchResponse,
    summary="Vector similarity search (top-K semantically relevant chunks)",
)
async def vector_search(
    payload: SearchRequest,
    service: VectorSearchService = Depends(get_search_service),
) -> SearchResponse:
    outcome = await service.search(payload.query, top_k=payload.top_k)
    return SearchResponse(
        query=payload.query,
        top_k=outcome.requested_top_k,
        count=outcome.returned,
        timings=_timings_out(outcome),
        results=[_result_out(r) for r in outcome.results],
    )


@router.post(
    "/debug",
    response_model=SearchDebugResponse,
    summary="Vector search diagnostics (query embedding stats + scores + timings)",
)
async def debug_search(
    payload: SearchRequest,
    service: VectorSearchService = Depends(get_search_service),
) -> SearchDebugResponse:
    outcome, stats = await service.run(payload.query, top_k=payload.top_k)
    return SearchDebugResponse(
        query=payload.query,
        top_k=outcome.requested_top_k,
        count=outcome.returned,
        query_embedding=QueryEmbeddingStatsOut(**asdict(stats)),
        timings=_timings_out(outcome),
        results=[_result_out(r) for r in outcome.results],
    )
