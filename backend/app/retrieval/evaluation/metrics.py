"""Retrieval metrics (Phase 2D).

Pure, dependency-free functions over a ranked list of relevance flags
(`flags[i]` = was the i-th retrieved result relevant?). The benchmark runner
produces the flags (by comparing results to ground truth) and the denominators;
these functions only do the arithmetic, so they are trivially unit-testable.

Metric definitions & why they matter
------------------------------------
* **Recall@K** = (relevant items in top-K) / (total relevant in corpus). "Did we
  find the relevant content that exists?" The primary retrieval-quality signal —
  if recall is low, no downstream re-ranking/RAG can recover the missing evidence.
* **Precision@K** = (relevant items in top-K) / (items returned in top-K). "How
  much of what we returned was on-target?" Controls noise fed to later stages.
* **MRR (Mean Reciprocal Rank)** = mean of 1/rank_of_first_relevant. Rewards
  putting a relevant chunk *high*; matters because downstream context windows are
  small, so the first hit's position is what counts.
* **Hit Rate@K** = fraction of queries with ≥1 relevant result in top-K. A
  coarse "did retrieval work at all?" gate.
* **Latency** = end-to-end retrieval time (tracked by the services). Quality is
  worthless if it's too slow on the hot path.
* **Candidate Reduction %** = 1 - (candidates considered / corpus size). How much
  metadata filtering narrowed the search space (0% for pure vector search).
"""

from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(flags: Sequence[bool], total_relevant: int, k: int) -> float:
    """Relevant retrieved in top-K over total relevant available."""
    if total_relevant <= 0:
        return 0.0
    hits = sum(1 for f in flags[:k] if f)
    return hits / total_relevant


def precision_at_k(flags: Sequence[bool], k: int) -> float:
    """Relevant retrieved in top-K over the number actually returned in top-K.

    Denominator is `min(k, len(flags))` so returning fewer than k items is not
    penalised as if the missing slots were wrong.
    """
    topk = list(flags[:k])
    if not topk:
        return 0.0
    return sum(1 for f in topk if f) / len(topk)


def reciprocal_rank(flags: Sequence[bool]) -> float:
    """1 / rank of the first relevant result (1-indexed); 0 if none relevant."""
    for i, f in enumerate(flags, start=1):
        if f:
            return 1.0 / i
    return 0.0


def hit_rate_at_k(flags: Sequence[bool], k: int) -> float:
    """1.0 if any relevant result appears in top-K, else 0.0 (per query)."""
    return 1.0 if any(flags[:k]) else 0.0


def candidate_reduction_pct(corpus_size: int, candidate_count: int) -> float:
    """Percentage of the corpus excluded by filtering before ranking."""
    if corpus_size <= 0:
        return 0.0
    reduction = 1.0 - (candidate_count / corpus_size)
    return round(max(0.0, reduction) * 100.0, 2)


def mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0
