"""Pydantic schemas for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from app.models.enums import MemoStatus, MemoType


class CitationSchema(BaseModel):
    """Reference tracking for statements in the generated memo."""

    report_id: uuid.UUID
    chunk_id: uuid.UUID | None = None
    page_number: int | None = None
    section_name: str | None = None
    source_type: str  # e.g., 'financial_metric', 'risk_factor', 'management_tone', 'text_chunk'
    text_snippet: str | None = None


class MemoSectionSchema(BaseModel):
    """A single section of the investment memo."""

    section_name: str
    section_order: int
    content: str
    citations: list[CitationSchema] = Field(default_factory=list)


class MemoDetailsResponse(BaseModel):
    """Full details of a generated investment memo."""

    id: uuid.UUID
    company_id: uuid.UUID
    report_id: uuid.UUID
    benchmark_run_id: uuid.UUID | None = None
    memo_type: MemoType
    status: MemoStatus
    title: str
    executive_summary: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    sections: list[MemoSectionOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class MemoSectionOut(BaseModel):
    """Output schema for a memo section."""

    id: uuid.UUID
    memo_id: uuid.UUID
    section_name: str
    section_order: int
    content: str
    citations: list[CitationSchema] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemoGenerationRequest(BaseModel):
    """Request schema to trigger memo generation."""

    company_id: uuid.UUID
    report_id: uuid.UUID
    benchmark_run_id: uuid.UUID | None = None
    memo_type: MemoType = MemoType.SINGLE_COMPANY
    title: str | None = None


class MemoGenerationResponse(BaseModel):
    """Response returned upon enqueuing memo generation."""

    memo_id: uuid.UUID
    status: MemoStatus
    message: str


class MemoExportResponse(BaseModel):
    """Export container for the investment memo."""

    memo_id: uuid.UUID
    title: str
    format: str  # 'markdown' | 'json'
    exported_content: str  # raw string or json-stringified content


# ---- Package Builder schemas ----

class FinancialMetricPack(BaseModel):
    name: str
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    category: str


class MetricComparisonPack(BaseModel):
    metric_name: str
    comparison_type: str
    current_value: float | None = None
    previous_value: float | None = None
    change_pct: float | None = None


class FinancialAnalyticsPack(BaseModel):
    signal_type: str
    metric_name: str
    trend: str | None = None
    strength: float | None = None
    score: float | None = None
    explanation: str | None = None


class RiskFactorPack(BaseModel):
    id: uuid.UUID
    category: str
    severity: str
    description: str
    source_chunk_id: uuid.UUID | None = None
    page_number: int | None = None


class ManagementTonePack(BaseModel):
    sentiment: str
    confidence_level: str
    hedging_score: float
    sentiment_score: float
    source_chunk_id: uuid.UUID | None = None


class BenchmarkSummaryPack(BaseModel):
    overall_score: float | None = None
    financial_score: float | None = None
    risk_score: float | None = None
    tone_score: float | None = None
    capital_allocation_score: float | None = None
    rank: int | None = None


class TextChunkPack(BaseModel):
    id: uuid.UUID
    content: str
    page_number: int | None = None
    section_name: str | None = None


class MemoPackage(BaseModel):
    """Consolidated inputs packaging all structured intelligence for LLM consumption."""

    company_name: str
    report_id: uuid.UUID
    report_title: str
    reporting_year: int | None = None
    reporting_period: str | None = None
    financial_metrics: list[FinancialMetricPack] = Field(default_factory=list)
    comparisons: list[MetricComparisonPack] = Field(default_factory=list)
    analytics: list[FinancialAnalyticsPack] = Field(default_factory=list)
    risks: list[RiskFactorPack] = Field(default_factory=list)
    tones: list[ManagementTonePack] = Field(default_factory=list)
    benchmark: BenchmarkSummaryPack | None = None
    retrieved_evidence: list[TextChunkPack] = Field(default_factory=list)
