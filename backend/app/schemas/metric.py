"""Pydantic schemas for financial-metric inspection (Phase 3A).

Inspection only — no analytics, no YoY/QoQ, no comparisons (later phases).
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.enums import ReportStatus


class MetricOut(BaseModel):
    id: uuid.UUID
    report_id: uuid.UUID
    source_chunk_id: uuid.UUID | None
    metric_name: str
    normalized_metric_name: str
    metric_category: str
    value: float
    currency: str | None
    unit: str
    fiscal_year: int | None
    fiscal_quarter: int | None
    confidence_score: float
    extraction_method: str
    source_text: str
    extraction_metadata: dict


class MetricListResponse(BaseModel):
    report_id: uuid.UUID
    count: int
    items: list[MetricOut]


class MetricSummaryResponse(BaseModel):
    report_id: uuid.UUID
    total: int
    avg_confidence: float
    by_category: dict[str, int]
    by_method: dict[str, int]
    by_metric: dict[str, int]


class MetricExtractResponse(BaseModel):
    report_id: uuid.UUID
    report_status: ReportStatus
    task_enqueued: bool
    detail: str
