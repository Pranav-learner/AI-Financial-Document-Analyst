"""Pydantic models (schemas) for Competitor Benchmarking (Phase 8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BenchmarkDimension, BenchmarkStatus


class BenchmarkRunCreate(BaseModel):
    run_name: str = Field(..., description="Human-readable name for the benchmark run")
    company_ids: list[uuid.UUID] = Field(
        ..., min_items=2, description="Cohort of company IDs to benchmark (at least 2)"
    )
    benchmark_type: str = Field("cohort", description="Type of benchmark (e.g., cohort, time_series)")
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional execution configuration (e.g. weights, reporting_year)",
    )


class BenchmarkRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_name: str
    company_ids: list[uuid.UUID]
    benchmark_type: str
    configuration: dict[str, Any]
    status: BenchmarkStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class BenchmarkResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benchmark_run_id: uuid.UUID
    company_id: uuid.UUID
    benchmark_dimension: BenchmarkDimension
    metric_name: str
    metric_value: float | None = None
    rank: int | None = None
    percentile: float | None = None
    score: float | None = None
    created_at: datetime


class BenchmarkSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benchmark_run_id: uuid.UUID
    company_id: uuid.UUID
    financial_score: float | None = None
    risk_score: float | None = None
    tone_score: float | None = None
    capital_allocation_score: float | None = None
    overall_score: float | None = None
    rank: int | None = None
    created_at: datetime


class BenchmarkRunDetailsResponse(BaseModel):
    run: BenchmarkRunResponse
    summaries: list[BenchmarkSummaryResponse] = []
    results: list[BenchmarkResultResponse] = []


class BenchmarkComparisonRequest(BaseModel):
    company_ids: list[uuid.UUID] = Field(
        ..., min_items=2, description="Cohort of company IDs to compare (at least 2)"
    )
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional weights configuration and period overrides",
    )


class CompanySummaryPoint(BaseModel):
    company_id: uuid.UUID
    company_name: str
    ticker: str | None = None
    scores: dict[str, float | None] = {}  # dimension -> score
    rank: int | None = None


class CohortComparisonPoint(BaseModel):
    metric_name: str
    dimension: str
    values: dict[str, float | None] = {}  # str(company_id) -> raw value
    ranks: dict[str, int | None] = {}  # str(company_id) -> metric rank
    percentiles: dict[str, float | None] = {}  # str(company_id) -> metric percentile
    scores: dict[str, float | None] = {}  # str(company_id) -> metric normalized score


class BenchmarkComparisonResponse(BaseModel):
    cohort_summaries: list[CompanySummaryPoint]
    cohort_results: list[CohortComparisonPoint]
    configuration: dict[str, Any]
