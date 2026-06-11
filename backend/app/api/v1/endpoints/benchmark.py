"""Competitor Benchmarking API Router (Phase 8)."""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.benchmarking.benchmark_models import (
    BenchmarkComparisonRequest,
    BenchmarkComparisonResponse,
    BenchmarkResultResponse,
    BenchmarkRunCreate,
    BenchmarkRunResponse,
    BenchmarkSummaryResponse,
)
from app.benchmarking.benchmark_service import BenchmarkService
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.benchmark import BenchmarkResult, BenchmarkRun, BenchmarkSummary
from app.tasks.benchmark import run_benchmark_task

router = APIRouter()


@router.post(
    "/run",
    response_model=BenchmarkRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a new competitor benchmarking run",
)
async def create_benchmark_run(
    payload: BenchmarkRunCreate,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    """Create a new benchmark run and enqueue its background processing task."""
    run = BenchmarkRun(
        run_name=payload.run_name,
        company_ids=payload.company_ids,
        benchmark_type=payload.benchmark_type,
        configuration=payload.configuration,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue task
    run_benchmark_task.delay(str(run.id))

    return run


@router.get(
    "/{run_id}",
    response_model=BenchmarkRunResponse,
    summary="Get status and details of a benchmarking run",
)
async def get_benchmark_run(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    """Get the current state/status of a specific benchmark run."""
    stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
    res = await db.execute(stmt)
    run = res.scalars().first()
    if not run:
        raise NotFoundError("Benchmark run not found", details={"run_id": str(run_id)})
    return run


@router.get(
    "/{run_id}/results",
    response_model=list[BenchmarkResultResponse],
    summary="Get detailed dimension results for a benchmark run",
)
async def get_benchmark_results(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[BenchmarkResultResponse]:
    """Retrieve all computed metrics, ranks, percentiles, and scores for a run."""
    # Verify run exists
    run_stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
    run_res = await db.execute(run_stmt)
    if not run_res.scalars().first():
        raise NotFoundError("Benchmark run not found", details={"run_id": str(run_id)})

    stmt = select(BenchmarkResult).where(BenchmarkResult.benchmark_run_id == run_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get(
    "/{run_id}/summary",
    response_model=list[BenchmarkSummaryResponse],
    summary="Get company-level scores and overall ranks for a benchmark run",
)
async def get_benchmark_summary(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[BenchmarkSummaryResponse]:
    """Retrieve aggregated dimension scores and final cohort rankings for a run."""
    # Verify run exists
    run_stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
    run_res = await db.execute(run_stmt)
    if not run_res.scalars().first():
        raise NotFoundError("Benchmark run not found", details={"run_id": str(run_id)})

    stmt = select(BenchmarkSummary).where(BenchmarkSummary.benchmark_run_id == run_id)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post(
    "/compare",
    response_model=BenchmarkComparisonResponse,
    summary="Synchronously compare a company cohort in-memory",
)
async def compare_cohort_sync(
    payload: BenchmarkComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkComparisonResponse:
    """Run full benchmarking calculations on a cohort synchronously without DB persistence."""
    service = BenchmarkService(db)
    result = await service.compare_cohort(
        company_ids=payload.company_ids,
        configuration=payload.configuration,
    )
    return result
