"""Pydantic schemas for period comparisons (Phase 3B).

Data only — no narratives, no insights, no recommendations.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.models.enums import ReportStatus


class ComparisonOut(BaseModel):
    id: uuid.UUID
    metric_id: uuid.UUID
    company_id: uuid.UUID
    metric_name: str
    comparison_type: str
    current_period: str
    previous_period: str
    current_value: float
    previous_value: float
    absolute_change: float | None
    percentage_change: float | None


class ComparisonListResponse(BaseModel):
    count: int
    items: list[ComparisonOut]


class ComparisonSummaryResponse(BaseModel):
    company_id: uuid.UUID
    total: int
    by_type: dict[str, int]
    by_metric: dict[str, int]
    items: list[ComparisonOut]


class ComparisonGenerateResponse(BaseModel):
    report_id: uuid.UUID
    report_status: ReportStatus
    task_enqueued: bool
    detail: str
