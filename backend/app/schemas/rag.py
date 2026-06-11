"""Pydantic schemas for Advanced Retrieval & RAG API (Phase 6)."""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field
from app.schemas.search import HybridFilters


class CitationOut(BaseModel):
    citation_id: int
    report_id: uuid.UUID
    chunk_id: uuid.UUID
    page_number: int | None = None
    section_name: str | None = None
    source_text_preview: str


class RAGRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language search query")
    strategy: str | None = Field(None, description="Retrieval strategy (e.g. FINANCIAL_METRICS, RISK_ANALYSIS)")
    top_k: int | None = Field(None, ge=5, le=50, description="Results to return (5–50)")
    filters: HybridFilters = Field(default_factory=HybridFilters)


class RAGRetrieveResponse(BaseModel):
    context_text: str
    tokens_used: int
    budget_limit: int
    citations: list[CitationOut]


class RAGDebugResponse(BaseModel):
    query: str
    strategy: str
    steps: dict
    context_text: str
    tokens_used: int
    budget_limit: int
    citations: list[CitationOut]
