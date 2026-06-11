"""Unit tests for retrieval metrics (Phase 2D)."""

from __future__ import annotations

import math

import pytest
from app.retrieval.evaluation import metrics


@pytest.mark.unit
def test_recall_at_k() -> None:
    # 2 relevant in top-3, 4 relevant total → 0.5
    flags = [True, False, True, False]
    assert metrics.recall_at_k(flags, total_relevant=4, k=3) == 0.5
    assert metrics.recall_at_k(flags, total_relevant=2, k=10) == 1.0


@pytest.mark.unit
def test_recall_zero_denominator() -> None:
    assert metrics.recall_at_k([True], total_relevant=0, k=5) == 0.0


@pytest.mark.unit
def test_precision_at_k() -> None:
    flags = [True, True, False, False]
    assert metrics.precision_at_k(flags, k=2) == 1.0
    assert metrics.precision_at_k(flags, k=4) == 0.5


@pytest.mark.unit
def test_precision_fewer_than_k_returned() -> None:
    # only 2 returned, both relevant, k=10 → 1.0 (not penalised for empty slots)
    assert metrics.precision_at_k([True, True], k=10) == 1.0


@pytest.mark.unit
def test_precision_empty() -> None:
    assert metrics.precision_at_k([], k=5) == 0.0


@pytest.mark.unit
@pytest.mark.parametrize(
    "flags,expected",
    [([True, False], 1.0), ([False, True], 0.5), ([False, False, True], 1 / 3), ([False], 0.0)],
)
def test_reciprocal_rank(flags, expected) -> None:
    assert math.isclose(metrics.reciprocal_rank(flags), expected)


@pytest.mark.unit
def test_hit_rate() -> None:
    assert metrics.hit_rate_at_k([False, False, True], k=3) == 1.0
    assert metrics.hit_rate_at_k([False, False, True], k=2) == 0.0
    assert metrics.hit_rate_at_k([], k=5) == 0.0


@pytest.mark.unit
def test_candidate_reduction() -> None:
    assert metrics.candidate_reduction_pct(1000, 100) == 90.0
    assert metrics.candidate_reduction_pct(1000, 1000) == 0.0     # no filter
    assert metrics.candidate_reduction_pct(0, 0) == 0.0
    assert metrics.candidate_reduction_pct(100, 200) == 0.0       # clamped, never negative


@pytest.mark.unit
def test_mean() -> None:
    assert metrics.mean([1.0, 2.0, 3.0]) == 2.0
    assert metrics.mean([]) == 0.0


@pytest.mark.unit
def test_ndcg_at_k() -> None:
    # perfect ranking
    assert metrics.ndcg_at_k([True, True, False], k=3) == 1.0
    # imperfect ranking
    flags = [False, True]
    # dcg = 0 / log(2) + 1 / log(3) = 1 / log2(3) = 0.6309
    # idcg = 1 / log(2) + 0 / log(3) = 1.0
    # ndcg = 0.6309
    assert math.isclose(metrics.ndcg_at_k(flags, k=2), 1.0 / math.log2(3))


@pytest.mark.unit
def test_ndcg_empty() -> None:
    assert metrics.ndcg_at_k([], k=5) == 0.0
    assert metrics.ndcg_at_k([False, False], k=2) == 0.0
