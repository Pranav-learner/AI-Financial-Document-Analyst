"""Reranking data models."""

from __future__ import annotations

from pydantic import BaseModel, Field
from app.retrieval.search.retrieval_models import SearchResult


class RerankResult(BaseModel):
    chunk_id: str
    original_score: float
    reranked_score: float
    chunk_text: str
    metadata: dict = Field(default_factory=dict)
