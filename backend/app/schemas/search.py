"""Pydantic schemas for the vector-search API (Phase 2B).

Retrieval only — these carry chunks + similarity scores, never answers.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural-language search query", min_length=1)
    top_k: int = Field(
        10, ge=5, le=50, description="Number of results to return (5–50, default 10)"
    )


class SearchResultOut(BaseModel):
    chunk_id: uuid.UUID
    report_id: uuid.UUID
    section_id: uuid.UUID | None
    score: float
    chunk_text: str
    metadata: dict


class SearchTimingsOut(BaseModel):
    embedding_ms: float
    vector_search_ms: float
    total_ms: float


class SearchResponse(BaseModel):
    query: str
    top_k: int
    count: int
    timings: SearchTimingsOut
    results: list[SearchResultOut]


class QueryEmbeddingStatsOut(BaseModel):
    dimension: int
    norm: float
    preview: list[float]
    model: str
    task_type: str


class SearchDebugResponse(BaseModel):
    """Retrieval diagnostics: query → embedding stats → chunks → scores → timings."""

    query: str
    top_k: int
    count: int
    query_embedding: QueryEmbeddingStatsOut
    timings: SearchTimingsOut
    results: list[SearchResultOut]
