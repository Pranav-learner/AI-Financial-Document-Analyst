"""Benchmark runner (Phase 2D).

Drives a benchmark suite through a retrieval strategy and computes metrics:

    for each query → run retrieval → judge results vs ground truth → metrics
    → aggregate into an EvaluationRun

Strategy-agnostic: it depends only on an async `retrieve` callable returning a
`RetrievalOutput`, so vector, hybrid, and any future strategy are evaluated the
same way (and are therefore directly comparable). The `total_relevant` callable
provides the per-query recall denominator (e.g. count of section-matching chunks).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.logging import get_logger
from app.retrieval.evaluation import metrics
from app.retrieval.evaluation.evaluation_models import EvaluationResult, EvaluationRun
from app.retrieval.evaluation.ground_truth import GroundTruthExample
from app.retrieval.search.retrieval_models import SearchResult

log = get_logger(__name__)


@dataclass
class RetrievalOutput:
    """What a retrieval strategy returns for one query (runner input)."""

    results: list[SearchResult]
    candidate_count: int
    latency_ms: float
    error: str | None = None
    extra: dict = field(default_factory=dict)


RetrieveFn = Callable[[GroundTruthExample, int], Awaitable[RetrievalOutput]]
TotalRelevantFn = Callable[[GroundTruthExample], Awaitable[int]]


def _now() -> str:
    return datetime.now(UTC).isoformat()


class BenchmarkRunner:
    def __init__(self, *, retrieval_type: str, corpus_size: int) -> None:
        self.retrieval_type = retrieval_type
        self.corpus_size = corpus_size

    async def run(
        self,
        examples: list[GroundTruthExample],
        retrieve: RetrieveFn,
        total_relevant: TotalRelevantFn,
        *,
        top_k: int,
    ) -> EvaluationRun:
        results: list[EvaluationResult] = []
        failures = 0

        # Lists to aggregate gains
        reranking_gains = []
        query_rewriting_gains = []
        hyde_gains = []

        for ex in examples:
            out = await retrieve(ex, top_k)
            if out.error is not None:
                failures += 1
                log.warning("evaluation.query_failed", query=ex.query, error=out.error)
                continue

            flags = [ex.is_relevant(r) for r in out.results]
            denom = await total_relevant(ex)

            # Extract gains from out.extra if present
            reranking_gains.append(out.extra.get("reranking_gain", 0.0))
            query_rewriting_gains.append(out.extra.get("query_rewriting_gain", 0.0))
            hyde_gains.append(out.extra.get("hyde_gain", 0.0))

            results.append(
                EvaluationResult(
                    query=ex.query,
                    category=ex.category,
                    retrieval_type=self.retrieval_type,
                    top_k=top_k,
                    recall_at_k=round(metrics.recall_at_k(flags, denom, top_k), 6),
                    precision_at_k=round(metrics.precision_at_k(flags, top_k), 6),
                    mrr=round(metrics.reciprocal_rank(flags), 6),
                    hit_rate=metrics.hit_rate_at_k(flags, top_k),
                    latency_ms=round(out.latency_ms, 2),
                    candidate_count=out.candidate_count,
                    candidate_reduction_pct=metrics.candidate_reduction_pct(
                        self.corpus_size, out.candidate_count
                    ),
                    returned=len(out.results),
                    total_relevant=denom,
                    timestamp=_now(),
                    ndcg=round(metrics.ndcg_at_k(flags, top_k), 6),
                )
            )

        return self._aggregate(
            results,
            top_k=top_k,
            failures=failures,
            mean_rerank_gain=metrics.mean(reranking_gains),
            mean_rewrite_gain=metrics.mean(query_rewriting_gains),
            mean_hyde_gain=metrics.mean(hyde_gains),
        )

    def _aggregate(
        self,
        results: list[EvaluationResult],
        *,
        top_k: int,
        failures: int,
        mean_rerank_gain: float = 0.0,
        mean_rewrite_gain: float = 0.0,
        mean_hyde_gain: float = 0.0,
    ) -> EvaluationRun:
        per_category: dict[str, dict] = {}
        by_cat: dict[str, list[EvaluationResult]] = {}
        for r in results:
            by_cat.setdefault(r.category, []).append(r)
        for cat, rs in sorted(by_cat.items()):
            per_category[cat] = {
                "num_queries": len(rs),
                "mean_recall_at_k": metrics.mean([r.recall_at_k for r in rs]),
                "mean_precision_at_k": metrics.mean([r.precision_at_k for r in rs]),
                "mean_mrr": metrics.mean([r.mrr for r in rs]),
                "hit_rate": metrics.mean([r.hit_rate for r in rs]),
                "mean_ndcg": metrics.mean([r.ndcg for r in rs]),
            }

        return EvaluationRun(
            run_id=str(uuid.uuid4()),
            retrieval_type=self.retrieval_type,
            top_k=top_k,
            num_queries=len(results),
            mean_recall_at_k=metrics.mean([r.recall_at_k for r in results]),
            mean_precision_at_k=metrics.mean([r.precision_at_k for r in results]),
            mean_mrr=metrics.mean([r.mrr for r in results]),
            hit_rate=metrics.mean([r.hit_rate for r in results]),
            mean_latency_ms=metrics.mean([r.latency_ms for r in results]),
            mean_candidate_reduction_pct=metrics.mean(
                [r.candidate_reduction_pct for r in results]
            ),
            corpus_size=self.corpus_size,
            failures=failures,
            timestamp=_now(),
            mean_ndcg=metrics.mean([r.ndcg for r in results]),
            reranking_gain=mean_rerank_gain,
            query_rewriting_gain=mean_rewrite_gain,
            hyde_gain=mean_hyde_gain,
            per_category=per_category,
            results=results,
        )
