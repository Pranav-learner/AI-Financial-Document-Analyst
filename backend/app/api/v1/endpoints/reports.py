"""Report ingestion endpoints (Phase 1A).

Routes are thin: they parse/shape HTTP, delegate to the service/repository, and
return schemas. No business logic lives here (docs/09 §). Mounted under
`/api/v1/reports`.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.ingestion.services.report_ingestion_service import ReportIngestionService
from app.models.enums import ReportType
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    ReportDetail,
    ReportListItem,
    ReportListResponse,
    ReportPageOut,
    ReportPagesResponse,
    ReportUploadResponse,
    SectionListResponse,
    SectionMapItem,
    SectionMapResponse,
    SectionOut,
    SectionSummary,
)

router = APIRouter()


@router.post(
    "/upload",
    response_model=ReportUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a financial PDF for ingestion",
)
async def upload_report(
    file: UploadFile = File(..., description="PDF document (10-K, 10-Q, transcript)"),
    report_type: ReportType = Form(...),
    year: int = Form(..., ge=1900, le=2200),
    quarter: int | None = Form(None, ge=1, le=4),
    ticker: str | None = Form(None, max_length=16),
    company_name: str | None = Form(None, max_length=255),
    db: AsyncSession = Depends(get_db),
) -> ReportUploadResponse:
    """Store the file, create a report record, and queue async processing."""
    data = await file.read()
    service = ReportIngestionService(db)
    report = await service.ingest_upload(
        data=data,
        original_filename=file.filename,
        content_type=file.content_type,
        report_type=report_type,
        year=year,
        quarter=quarter,
        ticker=ticker,
        company_name=company_name,
    )
    return ReportUploadResponse(report_id=report.id, status=report.status)


@router.get("", response_model=ReportListResponse, summary="List reports")
async def list_reports(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    repo = ReportRepository(db)
    rows, total = await repo.list_reports(limit=limit, offset=offset)
    return ReportListResponse(
        items=[ReportListItem.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportDetail, summary="Get report detail")
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportDetail:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    return ReportDetail.model_validate(report)


@router.get(
    "/{report_id}/pages",
    response_model=ReportPagesResponse,
    summary="Get extracted page text (debugging)",
)
async def get_report_pages(
    report_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ReportPagesResponse:
    repo = ReportRepository(db)
    report = await repo.get_report(report_id)
    if report is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    pages, total = await repo.get_pages(report_id, limit=limit, offset=offset)
    return ReportPagesResponse(
        report_id=report_id,
        total_pages=total,
        items=[ReportPageOut.model_validate(p) for p in pages],
        limit=limit,
        offset=offset,
    )


# ---- Phase 1B: sections ------------------------------------------------------


@router.get(
    "/{report_id}/sections",
    response_model=SectionListResponse,
    summary="List detected sections (no content)",
)
async def list_sections(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SectionListResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    sections = await repo.get_sections(report_id)
    return SectionListResponse(
        report_id=report_id,
        count=len(sections),
        items=[SectionSummary.model_validate(s) for s in sections],
    )


@router.get(
    "/{report_id}/section-map",
    response_model=SectionMapResponse,
    summary="Section boundary map (debug/visualization)",
)
async def section_map(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SectionMapResponse:
    repo = ReportRepository(db)
    if await repo.get_report(report_id) is None:
        raise NotFoundError("Report not found", details={"report_id": str(report_id)})
    sections = await repo.get_sections(report_id)
    return SectionMapResponse(
        report_id=report_id,
        sections=[
            SectionMapItem(
                section=s.normalized_section_name,
                start_page=s.start_page,
                end_page=s.end_page,
                confidence_score=float(s.confidence_score),
            )
            for s in sections
        ],
    )


@router.get(
    "/{report_id}/sections/{section_id}",
    response_model=SectionOut,
    summary="Get one detected section (with content)",
)
async def get_section(
    report_id: uuid.UUID,
    section_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SectionOut:
    repo = ReportRepository(db)
    section = await repo.get_section(section_id)
    if section is None or section.report_id != report_id:
        raise NotFoundError("Section not found", details={"section_id": str(section_id)})
    return SectionOut.model_validate(section)
