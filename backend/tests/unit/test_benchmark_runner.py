"""Unit tests for the BenchmarkRunner and EvaluationStore (Phase 2D)."""

from __future__ import annotations

import uuid

import pytest
from app.retrieval.evaluation.benchmark_runner import BenchmarkRunner, RetrievalOutput
from app.retrieval.evaluation.evaluation_models import EvaluationRun
from app.retrieval.evaluation.evaluation_service import EvaluationStore
from app.retrieval.evaluation.ground_truth import GroundTruthExample
from app.retrieval.search.retrieval_models import SearchResult


def _res(section: str) -> SearchResult:
    return SearchResult(
        chunk_id=uuid.uuid4(), report_id=uuid.uuid4(), section_id=None,
        score=0.9, chunk_text="x", metadata={"normalized_section_name": section},
    )


def _ex(eid: str, section: str) -> GroundTruthExample:
    return GroundTruthExample(id=eid, query=eid, category="RISK", expected_sections=(section,))


def _retriever(mapping, *, candidate_count=10, latency=5.0, errors=()):
    async def retrieve(ex, top_k):
        if ex.id in errors:
            return RetrievalOutput(results=[], candidate_count=0, latency_ms=0.0, error="boom")
        return RetrievalOutput(
            results=mapping[ex.id][:top_k], candidate_count=candidate_count, latency_ms=latency
        )
    return retrieve


def _total_relevant(n=2):
    async def fn(ex):
        return n
    return fn


@pytest.mark.unit
async def test_perfect_retrieval_metrics() -> None:
    ex = _ex("q1", "Risk Factors")
    mapping = {"q1": [_res("Risk Factors"), _res("Risk Factors")]}
    runner = BenchmarkRunner(retrieval_type="vector", corpus_size=100)
    run = await runner.run([ex], _retriever(mapping), _total_relevant(2), top_k=10)
    r = run.results[0]
    assert r.recall_at_k == 1.0       # 2 relevant / 2 total
    assert r.precision_at_k == 1.0
    assert r.mrr == 1.0
    assert r.hit_rate == 1.0
    assert r.candidate_reduction_pct == 90.0   # 100→10


@pytest.mark.unit
async def test_no_relevant_results() -> None:
    ex = _ex("q1", "Risk Factors")
    mapping = {"q1": [_res("MD&A"), _res("Business Overview")]}
    runner = BenchmarkRunner(retrieval_type="vector", corpus_size=100)
    run = await runner.run([ex], _retriever(mapping), _total_relevant(2), top_k=10)
    r = run.results[0]
    assert r.recall_at_k == 0.0 and r.precision_at_k == 0.0
    assert r.mrr == 0.0 and r.hit_rate == 0.0


@pytest.mark.unit
async def test_first_relevant_at_rank_two_gives_half_mrr() -> None:
    ex = _ex("q1", "Risk Factors")
    mapping = {"q1": [_res("MD&A"), _res("Risk Factors")]}
    runner = BenchmarkRunner(retrieval_type="hybrid", corpus_size=100)
    run = await runner.run([ex], _retriever(mapping), _total_relevant(2), top_k=10)
    assert run.results[0].mrr == 0.5


@pytest.mark.unit
async def test_aggregate_and_per_category() -> None:
    exs = [_ex("q1", "Risk Factors"), _ex("q2", "Risk Factors")]
    mapping = {"q1": [_res("Risk Factors")], "q2": [_res("MD&A")]}
    runner = BenchmarkRunner(retrieval_type="vector", corpus_size=10)
    run = await runner.run(exs, _retriever(mapping), _total_relevant(1), top_k=10)
    assert run.num_queries == 2
    assert run.hit_rate == 0.5                    # 1 of 2 queries hit
    assert "RISK" in run.per_category
    assert run.per_category["RISK"]["num_queries"] == 2


@pytest.mark.unit
async def test_failures_are_counted_not_scored() -> None:
    exs = [_ex("q1", "Risk Factors"), _ex("q2", "Risk Factors")]
    mapping = {"q1": [_res("Risk Factors")], "q2": []}
    runner = BenchmarkRunner(retrieval_type="vector", corpus_size=10)
    run = await runner.run(exs, _retriever(mapping, errors=("q2",)), _total_relevant(1), top_k=10)
    assert run.failures == 1
    assert run.num_queries == 1                   # only the successful query scored


@pytest.mark.unit
def test_store_ring_buffer_and_latest() -> None:
    store = EvaluationStore(max_runs=2)

    def _run(rtype):
        return EvaluationRun(
            run_id=str(uuid.uuid4()), retrieval_type=rtype, top_k=10, num_queries=1,
            mean_recall_at_k=0.5, mean_precision_at_k=0.5, mean_mrr=0.5, hit_rate=1.0,
            mean_latency_ms=1.0, mean_candidate_reduction_pct=0.0, corpus_size=1,
            failures=0, timestamp="t",
        )

    a, b, c = _run("vector"), _run("hybrid"), _run("vector")
    for run in (a, b, c):
        store.add(run)
    assert len(store.all()) == 2                   # ring buffer dropped the oldest
    latest = store.latest_by_type()
    assert latest["vector"].run_id == c.run_id     # newest vector wins
