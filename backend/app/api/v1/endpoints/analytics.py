"""Financial Analytics endpoints (Phase 3C).

Expose deterministic ratios, signals, and trend classifications. No narratives.
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.financial_analytics import FinancialAnalytics
from app.repositories.report_repository import ReportRepository
from app.schemas.analytics import (
    AnalyticsGenerateResponse,
    AnalyticsListResponse,
    AnalyticsOut,
    AnalyticsSummaryResponse,
)
from app.tasks.ingestion import generate_financial_analytics_task

router = APIRouter()


def _num(v) -> float | None:
    return float(v) if v is not None else None


def _out(a: FinancialAnalytics) -> AnalyticsOut:
    return AnalyticsOut(
        id=a.id,
        company_id=a.company_id,
        report_id=a.report_id,
        metric_name=a.metric_name,
        signal_type=a.signal_type,
        signal_code=a.signal_code,
        value=_num(a.value),
        classification=a.classification,
        severity=a.severity,
        supporting_metric_ids=a.supporting_metric_ids,
        explanation=a.explanation,
    )


@router.get(
    "/reports/{report_id}/analytics",
    response_model=AnalyticsListResponse,
    summary="Financial analytics for a report",
)
async def report_analytics(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsListResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    rows = await repo.get_analytics_by_report(report_id)
    return AnalyticsListResponse(count=len(rows), items=[_out(a) for a in rows])


@router.post(
    "/reports/{report_id}/analytics/generate",
    response_model=AnalyticsGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger financial analytics generation for a report",
)
async def generate_analytics(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsGenerateResponse:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    enqueue = report.company_id is not None
    if enqueue:
        generate_financial_analytics_task.delay(str(report_id))
    return AnalyticsGenerateResponse(
        report_id=report_id,
        report_status=report.status,
        task_enqueued=enqueue,
        detail="Analytics generation queued." if enqueue
        else "Report has no company; nothing to analyze.",
    )


@router.get(
    "/companies/{company_id}/analytics",
    response_model=AnalyticsListResponse,
    summary="All financial analytics for a company",
)
async def company_analytics(
    company_id: uuid.UUID,
    signal_type: str | None = Query(None, description="Filter by signal type (e.g. GROWTH, PROFITABILITY)"),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_analytics_by_company(company_id, signal_type=signal_type)
    return AnalyticsListResponse(count=len(rows), items=[_out(a) for a in rows])


@router.get(
    "/companies/{company_id}/analytics/signals",
    response_model=AnalyticsListResponse,
    summary="Retrieve signals for a company (ratios excluded)",
)
async def company_analytics_signals(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_analytics_by_company_signals(company_id)
    return AnalyticsListResponse(count=len(rows), items=[_out(a) for a in rows])


@router.get(
    "/companies/{company_id}/analytics/ratios",
    response_model=AnalyticsListResponse,
    summary="Retrieve ratios for a company (signals excluded)",
)
async def company_analytics_ratios(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_analytics_by_company_ratios(company_id)
    return AnalyticsListResponse(count=len(rows), items=[_out(a) for a in rows])


@router.get(
    "/companies/{company_id}/analytics-summary",
    response_model=AnalyticsSummaryResponse,
    summary="All analytics results for a company summarized",
)
async def company_analytics_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalyticsSummaryResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    rows = await repo.get_analytics_by_company(company_id)
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for a in rows:
        by_type[a.signal_type] = by_type.get(a.signal_type, 0) + 1
        by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
    return AnalyticsSummaryResponse(
        company_id=company_id,
        total=len(rows),
        by_type=dict(sorted(by_type.items())),
        by_severity=dict(sorted(by_severity.items())),
        items=[_out(a) for a in rows],
    )
