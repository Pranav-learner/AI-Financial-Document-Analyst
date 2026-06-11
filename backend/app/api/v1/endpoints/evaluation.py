"""Retrieval-evaluation endpoints (Phase 2D). Mounted at /api/v1/evaluation.

Run benchmark evaluations and inspect results/metrics/benchmarks (dashboard data
for an external UI — no frontend here). Measurement only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.retrieval.evaluation import (
    VALID_TYPES,
    EvaluationRun,
    EvaluationService,
    get_ground_truth,
    get_store,
)
from app.retrieval.evaluation.evaluation_exceptions import InvalidEvaluationRequestError
from app.schemas.evaluation import (
    BenchmarkExampleOut,
    BenchmarksResponse,
    EvaluationMetricsResponse,
    EvaluationResultOut,
    EvaluationResultsResponse,
    EvaluationRunOut,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationRunSummaryOut,
    StrategyComparison,
)

router = APIRouter()


def get_evaluation_service(db: AsyncSession = Depends(get_db)) -> EvaluationService:
    """Provide an evaluation service (injectable for tests)."""
    return EvaluationService(db)


def _run_out(run: EvaluationRun) -> EvaluationRunOut:
    return EvaluationRunOut(
        **run.summary(),
        results=[EvaluationResultOut(**r.as_dict()) for r in run.results],
    )


def _summary_out(run: EvaluationRun) -> EvaluationRunSummaryOut:
    return EvaluationRunSummaryOut(**run.summary())


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    summary="Run the retrieval benchmark suite and record results",
)
async def run_evaluation(
    payload: EvaluationRunRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    if payload.retrieval_type not in (*VALID_TYPES, "both"):
        raise InvalidEvaluationRequestError(
            "retrieval_type must be 'vector', 'hybrid', 'rag', or 'both'",
            details={"retrieval_type": payload.retrieval_type},
        )
    runs = await service.run(retrieval_type=payload.retrieval_type, top_k=payload.top_k)
    return EvaluationRunResponse(runs=[_run_out(r) for r in runs])


@router.get(
    "/results",
    response_model=EvaluationResultsResponse,
    summary="List recorded evaluation runs (newest first)",
)
async def list_results() -> EvaluationResultsResponse:
    runs = list(reversed(get_store().all()))
    return EvaluationResultsResponse(
        count=len(runs), runs=[_summary_out(r) for r in runs]
    )


@router.get(
    "/metrics",
    response_model=EvaluationMetricsResponse,
    summary="Latest metrics per strategy + hybrid-vs-vector comparison",
)
async def metrics() -> EvaluationMetricsResponse:
    latest = get_store().latest_by_type()
    comparison = None
    if "vector" in latest and "hybrid" in latest:
        v, h = latest["vector"], latest["hybrid"]
        comparison = StrategyComparison(
            recall_at_k_delta=round(h.mean_recall_at_k - v.mean_recall_at_k, 6),
            precision_at_k_delta=round(h.mean_precision_at_k - v.mean_precision_at_k, 6),
            mrr_delta=round(h.mean_mrr - v.mean_mrr, 6),
            hit_rate_delta=round(h.hit_rate - v.hit_rate, 6),
            hybrid_candidate_reduction_pct=h.mean_candidate_reduction_pct,
            latency_ms_delta=round(h.mean_latency_ms - v.mean_latency_ms, 2),
        )
    return EvaluationMetricsResponse(
        latest={t: _summary_out(r) for t, r in latest.items()},
        comparison=comparison,
    )


@router.get(
    "/benchmarks",
    response_model=BenchmarksResponse,
    summary="List the retrieval benchmark suite (ground truth)",
)
async def benchmarks() -> BenchmarksResponse:
    examples = get_ground_truth()
    return BenchmarksResponse(
        count=len(examples),
        categories=sorted({e.category for e in examples}),
        examples=[
            BenchmarkExampleOut(
                id=e.id,
                query=e.query,
                category=e.category,
                expected_sections=list(e.expected_sections),
                profile=e.profile,
                filters=e.filters,
            )
            for e in examples
        ],
    )
