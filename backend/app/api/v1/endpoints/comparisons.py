"""Period-comparison endpoints (Phase 3B). Full paths (report- and company-scoped).

Expose deterministic YoY/QoQ comparison data + an extraction trigger. No narratives.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.metric_comparison import MetricComparison
from app.repositories.report_repository import ReportRepository
from app.schemas.comparison import (
    ComparisonGenerateResponse,
    ComparisonListResponse,
    ComparisonOut,
    ComparisonSummaryResponse,
)
from app.tasks.ingestion import generate_metric_comparisons_task

router = APIRouter()


def _num(v) -> float | None:
    return float(v) if v is not None else None


def _out(c: MetricComparison) -> ComparisonOut:
    return ComparisonOut(
        id=c.id,
        metric_id=c.metric_id,
        company_id=c.company_id,
        metric_name=c.metric_name,
        comparison_type=c.comparison_type,
        current_period=c.current_period,
        previous_period=c.previous_period,
        current_value=float(c.current_value),
        previous_value=float(c.previous_value),
        absolute_change=_num(c.absolute_change),
        percentage_change=_num(c.percentage_change),
    )


@router.get(
    "/reports/{report_id}/comparisons",
    response_model=ComparisonListResponse,
    summary="Period comparisons for a report's metrics",
)
async def report_comparisons(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ComparisonListResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    rows = await repo.get_comparisons_by_report(report_id)
    return ComparisonListResponse(count=len(rows), items=[_out(c) for c in rows])


@router.post(
    "/reports/{report_id}/comparisons/generate",
    response_model=ComparisonGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger period-comparison generation for a report",
)
async def generate_comparisons(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ComparisonGenerateResponse:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    enqueue = report.company_id is not None
    if enqueue:
        generate_metric_comparisons_task.delay(str(report_id))
    return ComparisonGenerateResponse(
        report_id=report_id,
        report_status=report.status,
        task_enqueued=enqueue,
        detail="Comparison generation queued." if enqueue
        else "Report has no company; nothing to compare.",
    )


@router.get(
    "/companies/{company_id}/comparisons",
    response_model=ComparisonListResponse,
    summary="All period comparisons for a company",
)
async def company_comparisons(
    company_id: uuid.UUID,
    comparison_type: str | None = Query(None, description="Filter by YOY/QOQ/YTD/TTM"),
    db: AsyncSession = Depends(get_db),
) -> ComparisonListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_comparisons_by_company(company_id, comparison_type=comparison_type)
    return ComparisonListResponse(count=len(rows), items=[_out(c) for c in rows])


@router.get(
    "/companies/{company_id}/comparison-summary",
    response_model=ComparisonSummaryResponse,
    summary="All comparison results for a company (data only, no narrative)",
)
async def company_comparison_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ComparisonSummaryResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_comparisons_by_company(company_id)
    by_type: dict[str, int] = {}
    by_metric: dict[str, int] = {}
    for c in rows:
        by_type[c.comparison_type] = by_type.get(c.comparison_type, 0) + 1
        by_metric[c.metric_name] = by_metric.get(c.metric_name, 0) + 1
    return ComparisonSummaryResponse(
        company_id=company_id,
        total=len(rows),
        by_type=dict(sorted(by_type.items())),
        by_metric=dict(sorted(by_metric.items())),
        items=[_out(c) for c in rows],
    )


@router.get(
    "/companies/{company_id}/comparisons/{metric_name}",
    response_model=ComparisonListResponse,
    summary="Period comparisons for one metric of a company",
)
async def company_metric_comparisons(
    company_id: uuid.UUID,
    metric_name: str,
    db: AsyncSession = Depends(get_db),
) -> ComparisonListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_comparisons_by_company_metric(company_id, metric_name)
    return ComparisonListResponse(count=len(rows), items=[_out(c) for c in rows])
