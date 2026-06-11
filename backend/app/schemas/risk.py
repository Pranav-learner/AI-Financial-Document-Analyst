"""Pydantic schemas for risk extraction and evolution (Phase 4)."""

from __future__ import annotations

import uuid
from pydantic import BaseModel

from app.models.enums import ReportStatus


class RiskOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    report_id: uuid.UUID
    source_chunk_id: uuid.UUID | None
    risk_name: str
    normalized_risk_name: str
    risk_description: str
    category: str
    severity: str
    confidence_score: float
    extraction_method: str
    source_text: str
    extraction_metadata: dict


class RiskListResponse(BaseModel):
    report_id: uuid.UUID | None = None
    count: int
    items: list[RiskOut]


class RiskEvolutionOut(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    current_risk_id: uuid.UUID | None
    previous_risk_id: uuid.UUID | None
    evolution_type: str
    confidence_score: float
    explanation: str


class RiskEvolutionListResponse(BaseModel):
    company_id: uuid.UUID
    count: int
    items: list[RiskEvolutionOut]


class RiskSummaryResponse(BaseModel):
    company_id: uuid.UUID
    total_risks: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    evolution_counts: dict[str, int]


class RiskExtractResponse(BaseModel):
    report_id: uuid.UUID
    report_status: ReportStatus
    task_enqueued: bool
    detail: str
