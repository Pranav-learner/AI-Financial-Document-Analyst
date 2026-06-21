"""FastAPI Router for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations

import json
import uuid
from fastapi import APIRouter, Depends, Query, status, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RoleChecker
from app.services.rate_limiter import RateLimitCheck
from app.services.cache_service import CacheService, cache_endpoint
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db, SyncSessionLocal
from app.services.pdf_generator import PDFMemoGenerator
from app.memo.memo_package_builder import MemoPackageBuilder

from app.models.memo import InvestmentMemo, MemoSection
from app.models.enums import MemoStatus, UserRole
from app.memo.memo_models import (
    MemoGenerationRequest,
    MemoGenerationResponse,
    MemoDetailsResponse,
    MemoSectionOut,
    MemoExportResponse,
    CitationSchema,
)
from app.tasks.memo import generate_memo_task

router = APIRouter()


@router.post(
    "",
    response_model=MemoGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a new investment memo generation task",
    dependencies=[
        Depends(RoleChecker(UserRole.ANALYST)),
        Depends(RateLimitCheck(limit=10, window_seconds=60, scope="user")),
    ],
)
async def generate_memo(
    payload: MemoGenerationRequest,
    db: AsyncSession = Depends(get_db),
) -> MemoGenerationResponse:
    """Trigger the asynchronous generation of a structured investment memo."""
    # Check if a memo already exists for this report and company
    stmt = select(InvestmentMemo).where(
        InvestmentMemo.company_id == payload.company_id,
        InvestmentMemo.report_id == payload.report_id,
    )
    res = await db.execute(stmt)
    existing = res.scalars().first()

    if existing:
        # If it failed or is completed, we can trigger regeneration
        memo = existing
        memo.status = MemoStatus.PENDING
        memo.benchmark_run_id = payload.benchmark_run_id or memo.benchmark_run_id
        if payload.title:
            memo.title = payload.title
    else:
        memo_title = payload.title or "Investment Memo"
        memo = InvestmentMemo(
            company_id=payload.company_id,
            report_id=payload.report_id,
            benchmark_run_id=payload.benchmark_run_id,
            memo_type=payload.memo_type,
            status=MemoStatus.PENDING,
            title=memo_title,
            metadata_fields={"initialized_at": uuid.uuid4().hex}
        )
        db.add(memo)

    await db.commit()
    await db.refresh(memo)

    # Dispatch Celery task
    generate_memo_task.delay(str(memo.id))

    return MemoGenerationResponse(
        memo_id=memo.id,
        status=memo.status,
        message="Memo generation task enqueued successfully."
    )

@router.get(
    "/{memo_id}",
    response_model=MemoDetailsResponse,
    summary="Retrieve details and status of an investment memo",
)
async def get_memo_details(
    memo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MemoDetailsResponse:
    """Retrieve an investment memo including status and all sections."""
    cache_key = f"memo:details:{memo_id}"
    cached_val = await CacheService.get(cache_key)
    if cached_val:
        return MemoDetailsResponse(**cached_val)

    stmt = select(InvestmentMemo).where(InvestmentMemo.id == memo_id)
    res = await db.execute(stmt)
    memo = res.scalars().first()
    if not memo:
        raise NotFoundError("Investment memo not found", details={"memo_id": str(memo_id)})

    # Fetch sections ordered
    sec_stmt = select(MemoSection).where(MemoSection.memo_id == memo_id).order_by(MemoSection.section_order)
    sec_res = await db.execute(sec_stmt)
    sections = sec_res.scalars().all()

    # Build response model
    details = MemoDetailsResponse(
        id=memo.id,
        company_id=memo.company_id,
        report_id=memo.report_id,
        benchmark_run_id=memo.benchmark_run_id,
        memo_type=memo.memo_type,
        status=memo.status,
        title=memo.title,
        executive_summary=memo.executive_summary,
        content=memo.content,
        metadata=memo.metadata_fields,
        created_at=memo.created_at,
        updated_at=memo.updated_at,
        sections=[
            MemoSectionOut(
                id=s.id,
                memo_id=s.memo_id,
                section_name=s.section_name,
                section_order=s.section_order,
                content=s.content,
                citations=[CitationSchema(**c) for c in s.citations],
                created_at=s.created_at,
                updated_at=s.updated_at
            )
            for s in sections
        ]
    )

    if memo.status == MemoStatus.COMPLETED:
        await CacheService.set(cache_key, details.model_dump(), ttl=3600)

    return details


@router.get(
    "/{memo_id}/citations",
    response_model=list[CitationSchema],
    summary="Retrieve all citations associated with a generated memo",
)
async def get_memo_citations(
    memo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[CitationSchema]:
    """Compile and list all citations extracted across all memo sections."""
    stmt = select(InvestmentMemo).where(InvestmentMemo.id == memo_id)
    res = await db.execute(stmt)
    memo = res.scalars().first()
    if not memo:
        raise NotFoundError("Investment memo not found", details={"memo_id": str(memo_id)})

    sec_stmt = select(MemoSection).where(MemoSection.memo_id == memo_id).order_by(MemoSection.section_order)
    sec_res = await db.execute(sec_stmt)
    sections = sec_res.scalars().all()

    all_citations = []
    for s in sections:
        for c in s.citations:
            all_citations.append(CitationSchema(**c))
    return all_citations


@router.get(
    "/{memo_id}/export",
    response_model=MemoExportResponse,
    summary="Export generated memo as Markdown or JSON structure",
)
async def export_memo(
    memo_id: uuid.UUID,
    format: str = Query("markdown", regex="^(markdown|json)$"),
    db: AsyncSession = Depends(get_db),
) -> MemoExportResponse:
    """Exports the investment memo to a standardized format."""
    # Re-use details retrieval
    memo_details = await get_memo_details(memo_id=memo_id, db=db)
    if memo_details.status != MemoStatus.COMPLETED:
        raise ValidationError(
            f"Cannot export memo in status '{memo_details.status}'. Memo must be COMPLETED.",
            details={"memo_id": str(memo_id)}
        )

    if format == "json":
        exported_content = memo_details.model_dump_json(indent=2)
    else:
        # Markdown compilation
        md_lines = [
            f"# {memo_details.title}\n",
            "## Executive Summary",
            f"{memo_details.executive_summary}\n",
        ]
        
        for idx, sec in enumerate(memo_details.sections, start=1):
            md_lines.append(f"## {sec.section_name}")
            md_lines.append(f"{sec.content}\n")
            
            if sec.citations:
                md_lines.append("**Citations & Sources:**")
                for c_idx, cit in enumerate(sec.citations, start=1):
                    snippet = f' - "{cit.text_snippet[:80]}..."' if cit.text_snippet else ""
                    page_str = f" Page {cit.page_number}" if cit.page_number else ""
                    md_lines.append(f"[{c_idx}] {cit.source_type.upper()}{page_str}{snippet}")
                md_lines.append("")

        exported_content = "\n".join(md_lines)

    return MemoExportResponse(
        memo_id=memo_id,
        title=memo_details.title,
        format=format,
        exported_content=exported_content
    )


@router.get(
    "/{memo_id}/pdf",
    summary="Export generated memo as a publication-grade PDF document",
)
async def export_memo_pdf(
    memo_id: uuid.UUID,
) -> Response:
    """Generates and downloads a professional, publication-quality A4 PDF of the investment memo."""
    def generate_pdf_sync(m_id: uuid.UUID):
        with SyncSessionLocal() as session:
            # 1. Fetch memo
            stmt = select(InvestmentMemo).where(InvestmentMemo.id == m_id)
            memo = session.scalar(stmt)
            if not memo:
                raise NotFoundError("Investment memo not found", details={"memo_id": str(m_id)})
            
            if memo.status != MemoStatus.COMPLETED:
                raise ValidationError(
                    f"Cannot export PDF for memo in status '{memo.status}'. Memo must be COMPLETED.",
                    details={"memo_id": str(m_id)}
                )
            
            # 2. Reconstruct package
            package_builder = MemoPackageBuilder(session)
            package = package_builder.build(
                company_id=memo.company_id,
                report_id=memo.report_id,
                benchmark_run_id=memo.benchmark_run_id
            )
            
            # 3. Generate PDF bytes
            pdf_gen = PDFMemoGenerator(memo, package)
            return pdf_gen.build_pdf(), memo.title

    try:
        pdf_bytes, title = await run_in_threadpool(generate_pdf_sync, memo_id)
    except NotFoundError as exc:
        raise exc
    except ValidationError as exc:
        raise exc
    except Exception as exc:
        raise ValidationError(f"Failed to generate PDF: {exc}", details={"memo_id": str(memo_id)})

    # Return as attachment or inline download
    filename = f"{title.replace(' ', '_').lower()}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers
    )

