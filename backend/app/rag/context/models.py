"""RAG context models."""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_id: int
    report_id: uuid.UUID
    chunk_id: uuid.UUID
    page_number: int | None = None
    section_name: str | None = None
    source_text_preview: str


class ContextChunk(BaseModel):
    chunk_id: uuid.UUID
    report_id: uuid.UUID
    text: str
    page_number: int | None = None
    section_name: str | None = None
    score: float
    citation_id: int


class ContextPackage(BaseModel):
    context_text: str
    tokens_used: int
    budget_limit: int
    citations: list[Citation] = Field(default_factory=list)
