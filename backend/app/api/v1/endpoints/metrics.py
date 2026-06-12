"""Financial-metric endpoints (Phase 3A). Mounted under /api/v1/reports.

Inspect extracted metrics + trigger extraction. No analytics, no comparisons.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.financial_metric import FinancialMetric
from app.repositories.report_repository import ReportRepository
from app.schemas.metric import (
    MetricExtractResponse,
    MetricListResponse,
    MetricOut,
    MetricSummaryResponse,
)
from app.tasks.ingestion import extract_financial_metrics_task

router = APIRouter()


def _metric_out(m: FinancialMetric) -> MetricOut:
    return MetricOut(
        id=m.id,
        report_id=m.report_id,
        source_chunk_id=m.source_chunk_id,
        metric_name=m.metric_name,
        normalized_metric_name=m.normalized_metric_name,
        metric_category=m.metric_category,
        value=float(m.value),
        currency=m.currency,
        unit=m.unit,
        fiscal_year=m.fiscal_year,
        fiscal_quarter=m.fiscal_quarter,
        confidence_score=float(m.confidence_score),
        extraction_method=m.extraction_method,
        source_text=m.source_text,
        extraction_metadata=m.extraction_metadata or {},
    )


@router.get(
    "/{report_id}/metrics",
    response_model=MetricListResponse,
    summary="List extracted financial metrics for a report",
)
async def list_metrics(
    report_id: uuid.UUID,
    category: str | None = Query(None, description="Filter by metric_category"),
    db: AsyncSession = Depends(get_db),
) -> MetricListResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    metrics = await repo.get_metrics(report_id, category=category)
    return MetricListResponse(
        report_id=report_id,
        count=len(metrics),
        items=[_metric_out(m) for m in metrics],
    )


@router.get(
    "/{report_id}/metrics/summary",
    response_model=MetricSummaryResponse,
    summary="Summary of extracted metrics (counts + confidence; no analytics)",
)
async def metrics_summary(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MetricSummaryResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    metrics = await repo.get_metrics(report_id)

    by_category: dict[str, int] = {}
    by_method: dict[str, int] = {}
    by_metric: dict[str, int] = {}
    for m in metrics:
        by_category[m.metric_category] = by_category.get(m.metric_category, 0) + 1
        by_method[m.extraction_method] = by_method.get(m.extraction_method, 0) + 1
        by_metric[m.normalized_metric_name] = by_metric.get(m.normalized_metric_name, 0) + 1
    avg_conf = (
        round(sum(float(m.confidence_score) for m in metrics) / len(metrics), 4)
        if metrics
        else 0.0
    )
    return MetricSummaryResponse(
        report_id=report_id,
        total=len(metrics),
        avg_confidence=avg_conf,
        by_category=dict(sorted(by_category.items())),
        by_method=dict(sorted(by_method.items())),
        by_metric=dict(sorted(by_metric.items())),
    )


@router.post(
    "/{report_id}/metrics/extract",
    response_model=MetricExtractResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger financial-metric extraction for a report",
    dependencies=[Depends(RoleChecker(UserRole.ANALYST))],
)
async def extract_metrics(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MetricExtractResponse:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    total_chunks = await repo.count_chunks_async(report_id)
    if total_chunks == 0:
        return MetricExtractResponse(
            report_id=report_id,
            report_status=report.status,
            task_enqueued=False,
            detail="Report has no chunks to extract from (run chunking first).",
        )
    extract_financial_metrics_task.delay(str(report_id))
    return MetricExtractResponse(
        report_id=report_id,
        report_status=report.status,
        task_enqueued=True,
        detail="Metric extraction queued.",
    )


@router.get(
    "/{report_id}/metrics/{metric_id}",
    response_model=MetricOut,
    summary="Get one extracted metric (with source text)",
)
async def get_metric(
    report_id: uuid.UUID,
    metric_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MetricOut:
    repo = ReportRepository(db)
    metric = await repo.get_metric(metric_id)
    if metric is None or metric.report_id != report_id:
        raise NotFoundError("Metric not found", details={"metric_id": str(metric_id)})
    return _metric_out(metric)
