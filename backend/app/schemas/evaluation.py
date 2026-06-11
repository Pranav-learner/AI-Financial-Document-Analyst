"""Pydantic schemas for the retrieval-evaluation API (Phase 2D).

Dashboard-data only (no UI): expose benchmark results, metric summaries/trends,
and the benchmark suite.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationRunRequest(BaseModel):
    retrieval_type: str = Field(
        "both", description="'vector' | 'hybrid' | 'both'"
    )
    top_k: int | None = Field(None, ge=5, le=50, description="K for the run (default 10)")


class EvaluationResultOut(BaseModel):
    query: str
    category: str
    retrieval_type: str
    top_k: int
    recall_at_k: float
    precision_at_k: float
    mrr: float
    hit_rate: float
    latency_ms: float
    candidate_count: int
    candidate_reduction_pct: float
    returned: int
    total_relevant: int
    timestamp: str


class EvaluationRunSummaryOut(BaseModel):
    run_id: str
    retrieval_type: str
    top_k: int
    num_queries: int
    mean_recall_at_k: float
    mean_precision_at_k: float
    mean_mrr: float
    hit_rate: float
    mean_latency_ms: float
    mean_candidate_reduction_pct: float
    corpus_size: int
    failures: int
    timestamp: str
    per_category: dict


class EvaluationRunOut(EvaluationRunSummaryOut):
    results: list[EvaluationResultOut]


class EvaluationRunResponse(BaseModel):
    runs: list[EvaluationRunOut]


class EvaluationResultsResponse(BaseModel):
    count: int
    runs: list[EvaluationRunSummaryOut]


class StrategyComparison(BaseModel):
    """Hybrid-minus-vector deltas (positive = hybrid better)."""

    recall_at_k_delta: float
    precision_at_k_delta: float
    mrr_delta: float
    hit_rate_delta: float
    hybrid_candidate_reduction_pct: float
    latency_ms_delta: float


class EvaluationMetricsResponse(BaseModel):
    latest: dict[str, EvaluationRunSummaryOut]
    comparison: StrategyComparison | None = None


class BenchmarkExampleOut(BaseModel):
    id: str
    query: str
    category: str
    expected_sections: list[str]
    profile: str | None = None
    filters: dict


class BenchmarksResponse(BaseModel):
    count: int
    categories: list[str]
    examples: list[BenchmarkExampleOut]
