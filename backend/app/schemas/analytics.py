"""Pydantic schemas for financial analytics (Phase 3C).

Data only — no trend narratives, no investment recommendations, no RAG.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel
from app.models.enums import ReportStatus


class AnalyticsOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    report_id: uuid.UUID
    metric_name: str | None
    signal_type: str
    signal_code: str
    value: float | None
    classification: str
    severity: str
    supporting_metric_ids: list[uuid.UUID] | None
    explanation: str


class AnalyticsListResponse(BaseModel):
    count: int
    items: list[AnalyticsOut]


class AnalyticsSummaryResponse(BaseModel):
    company_id: uuid.UUID
    total: int
    by_type: dict[str, int]
    by_severity: dict[str, int]
    items: list[AnalyticsOut]


class AnalyticsGenerateResponse(BaseModel):
    report_id: uuid.UUID
    report_status: ReportStatus
    task_enqueued: bool
    detail: str
