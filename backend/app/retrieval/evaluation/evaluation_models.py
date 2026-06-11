"""Evaluation data contracts (Phase 2D).

`EvaluationResult` is the per-query record; `EvaluationRun` aggregates a whole
benchmark suite for one retrieval strategy. Both are plain dataclasses so they
can be stored, compared across runs (improvement tracking), and serialized by the
API layer. Designed to be retrieval-strategy-agnostic — vector, hybrid, and any
future strategy (rewriting, HyDE, re-ranking) produce the SAME shapes, so they
are directly comparable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class EvaluationResult:
    """Metrics for a single benchmark query under one retrieval strategy."""

    query: str
    category: str
    retrieval_type: str          # "vector" | "hybrid" | future strategies
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

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvaluationRun:
    """Aggregate of a benchmark suite for one retrieval strategy."""

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
    per_category: dict[str, dict] = field(default_factory=dict)
    results: list[EvaluationResult] = field(default_factory=list)

    def summary(self) -> dict:
        """The run without the per-query detail (for list/trend views)."""
        d = asdict(self)
        d.pop("results", None)
        return d

    def as_dict(self) -> dict:
        return asdict(self)
