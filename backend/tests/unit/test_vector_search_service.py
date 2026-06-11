"""Unit tests for VectorSearchService orchestration (Phase 2B).

No DB, no network: a fake query embedder + a fake vector-search are injected so
top-K validation, ranking pass-through, timings, and stats are tested in isolation.
"""

from __future__ import annotations

import uuid

import pytest
from app.core.config import settings
from app.retrieval.search.retrieval_models import QueryEmbeddingStats, SearchResult
from app.retrieval.search.search_exceptions import InvalidTopKError
from app.retrieval.search.search_service import VectorSearchService

DIM = 4


class FakeEmbedder:
    def embed(self, query):
        stats = QueryEmbeddingStats(
            dimension=DIM, norm=1.0, preview=[0.1, 0.2], model="m", task_type="RETRIEVAL_QUERY"
        )
        return [0.1] * DIM, stats


class FakeVectorSearch:
    def __init__(self, results) -> None:
        self.results = results
        self.last_top_k = None
        self.last_vector = None

    async def search(self, vector, *, top_k):
        self.last_top_k = top_k
        self.last_vector = vector
        return self.results[:top_k]


def _results(n: int) -> list[SearchResult]:
    # descending scores so we can assert order is preserved (no re-ranking)
    return [
        SearchResult(
            chunk_id=uuid.uuid4(),
            report_id=uuid.uuid4(),
            section_id=None,
            score=round(1.0 - i * 0.05, 4),
            chunk_text=f"chunk {i}",
            metadata={"i": i},
        )
        for i in range(n)
    ]


def _service(results):
    svc = VectorSearchService(None, query_embedder=FakeEmbedder())
    svc.vector_search = FakeVectorSearch(results)
    return svc


@pytest.mark.unit
async def test_returns_results_with_timings_and_stats() -> None:
    svc = _service(_results(5))
    outcome, stats = await svc.run("cash flow", top_k=5)
    assert outcome.returned == 5
    assert outcome.requested_top_k == 5
    assert outcome.timings.total_ms >= 0.0
    assert stats.dimension == DIM


@pytest.mark.unit
async def test_default_top_k_applied() -> None:
    svc = _service(_results(20))
    outcome = await svc.search("revenue")
    assert outcome.requested_top_k == settings.search_default_top_k
    assert svc.vector_search.last_top_k == settings.search_default_top_k


@pytest.mark.unit
async def test_ranking_order_is_preserved() -> None:
    svc = _service(_results(6))
    outcome = await svc.search("supply chain", top_k=6)
    scores = [r.score for r in outcome.results]
    assert scores == sorted(scores, reverse=True)  # service does not re-rank


@pytest.mark.unit
@pytest.mark.parametrize("bad", [settings.search_min_top_k - 1, settings.search_max_top_k + 1, 0])
async def test_top_k_out_of_range_raises(bad: int) -> None:
    svc = _service(_results(3))
    with pytest.raises(InvalidTopKError):
        await svc.search("q", top_k=bad)


@pytest.mark.unit
async def test_empty_db_returns_no_results() -> None:
    svc = _service([])
    outcome = await svc.search("anything", top_k=10)
    assert outcome.returned == 0
    assert outcome.results == []
