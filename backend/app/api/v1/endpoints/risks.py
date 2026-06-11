"""Risk-intelligence endpoints (Phase 4).

Expose structured risk factors, risk evolution tracking, and aggregate summaries.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.risk_factor import RiskFactor
from app.models.risk_evolution import RiskEvolution
from app.repositories.report_repository import ReportRepository
from app.schemas.risk import (
    RiskExtractResponse,
    RiskListResponse,
    RiskOut,
    RiskEvolutionOut,
    RiskEvolutionListResponse,
    RiskSummaryResponse,
)
from app.tasks.ingestion import extract_risks_task

router = APIRouter()


def _risk_out(r: RiskFactor) -> RiskOut:
    return RiskOut(
        id=r.id,
        company_id=r.company_id,
        report_id=r.report_id,
        source_chunk_id=r.source_chunk_id,
        risk_name=r.risk_name,
        normalized_risk_name=r.normalized_risk_name,
        risk_description=r.risk_description,
        category=r.category,
        severity=r.severity,
        confidence_score=float(r.confidence_score),
        extraction_method=r.extraction_method,
        source_text=r.source_text,
        extraction_metadata=r.extraction_metadata or {},
    )


def _evolution_out(e: RiskEvolution) -> RiskEvolutionOut:
    return RiskEvolutionOut(
        id=e.id,
        company_id=e.company_id,
        current_risk_id=e.current_risk_id,
        previous_risk_id=e.previous_risk_id,
        evolution_type=e.evolution_type,
        confidence_score=float(e.confidence_score),
        explanation=e.explanation,
    )


@router.get(
    "/reports/{report_id}/risks",
    response_model=RiskListResponse,
    summary="List extracted risk factors for a report",
)
async def list_report_risks(
    report_id: uuid.UUID,
    category: str | None = Query(None, description="Filter by risk category"),
    db: AsyncSession = Depends(get_db),
) -> RiskListResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    risks = await repo.get_risks(report_id, category=category)
    return RiskListResponse(
        report_id=report_id,
        count=len(risks),
        items=[_risk_out(r) for r in risks],
    )


@router.post(
    "/reports/{report_id}/risks/extract",
    response_model=RiskExtractResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger risk factor extraction for a report",
)
async def extract_risks(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskExtractResponse:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    total_chunks = await repo.count_chunks_async(report_id)
    if total_chunks == 0:
        return RiskExtractResponse(
            report_id=report_id,
            report_status=report.status,
            task_enqueued=False,
            detail="Report has no chunks to extract from (run chunking first).",
        )
    extract_risks_task.delay(str(report_id))
    return RiskExtractResponse(
        report_id=report_id,
        report_status=report.status,
        task_enqueued=True,
        detail="Risk extraction queued.",
    )


@router.get(
    "/reports/{report_id}/risks/{risk_id}",
    response_model=RiskOut,
    summary="Get details of a specific risk factor",
)
async def get_report_risk(
    report_id: uuid.UUID,
    risk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskOut:
    repo = ReportRepository(db)
    risk = await repo.get_risk(risk_id)
    if risk is None or risk.report_id != report_id:
        raise NotFoundError("Risk not found", details={"risk_id": str(risk_id)})
    return _risk_out(risk)


@router.get(
    "/companies/{company_id}/risks",
    response_model=RiskListResponse,
    summary="List all risk factors for a company across reports",
)
async def list_company_risks(
    company_id: uuid.UUID,
    category: str | None = Query(None, description="Filter by risk category"),
    severity: str | None = Query(None, description="Filter by risk severity"),
    db: AsyncSession = Depends(get_db),
) -> RiskListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    risks = await repo.get_risks_by_company(company_id, category=category, severity=severity)
    return RiskListResponse(
        report_id=None,
        count=len(risks),
        items=[_risk_out(r) for r in risks],
    )


@router.get(
    "/companies/{company_id}/risk-evolution",
    response_model=RiskEvolutionListResponse,
    summary="List all risk evolution records for a company",
)
async def list_company_risk_evolution(
    company_id: uuid.UUID,
    evolution_type: str | None = Query(None, description="Filter by evolution type"),
    db: AsyncSession = Depends(get_db),
) -> RiskEvolutionListResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    evolutions = await repo.get_risk_evolutions_by_company(company_id, evolution_type=evolution_type)
    return RiskEvolutionListResponse(
        company_id=company_id,
        count=len(evolutions),
        items=[_evolution_out(e) for e in evolutions],
    )


@router.get(
    "/companies/{company_id}/risk-summary",
    response_model=RiskSummaryResponse,
    summary="Get summary distribution and evolution counts of risk factors for a company",
)
async def get_company_risk_summary(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RiskSummaryResponse:
    repo = ReportRepository(db)
    if await repo.get_company(company_id) is None:
        raise NotFoundError("Company not found", details={"company_id": str(company_id)})
    risks = await repo.get_risks_by_company(company_id)
    evolutions = await repo.get_risk_evolutions_by_company(company_id)

    by_category: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    evolution_counts: dict[str, int] = {}

    for r in risks:
        by_category[r.category] = by_category.get(r.category, 0) + 1
        by_severity[r.severity] = by_severity.get(r.severity, 0) + 1

    for e in evolutions:
        evolution_counts[e.evolution_type] = evolution_counts.get(e.evolution_type, 0) + 1

    return RiskSummaryResponse(
        company_id=company_id,
        total_risks=len(risks),
        by_category=dict(sorted(by_category.items())),
        by_severity=dict(sorted(by_severity.items())),
        evolution_counts=dict(sorted(evolution_counts.items())),
    )
