"""Evaluation service + in-memory results store (Phase 2D).

Wires the retrieval strategies (Phase 2B vector, Phase 2C hybrid) to the benchmark
runner and ground truth, computes the recall denominators from the DB, runs the
suite, and records each run in a process-local store that the dashboard APIs read.

The store is intentionally in-memory: evaluation runs are operational telemetry,
not domain data, so they need no migration. (Persisting to a table is a noted
future enhancement for cross-restart trend history.)

Strictly measurement: no retrieval *enhancement* lives here — vector and hybrid
are run exactly as Phases 2B/2C built them, then scored.
"""

from __future__ import annotations

from collections import deque

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document_chunk import DocumentChunk
from app.retrieval.evaluation.benchmark_runner import BenchmarkRunner, RetrievalOutput
from app.retrieval.evaluation.evaluation_models import EvaluationRun
from app.retrieval.evaluation.ground_truth import GroundTruthExample, get_ground_truth
from app.retrieval.hybrid import HybridRetrievalService, RetrievalContext
from app.retrieval.search import QueryEmbedder, VectorSearchService
from app.retrieval.search.search_exceptions import SearchError

log = get_logger(__name__)

VALID_TYPES = ("vector", "hybrid")


class EvaluationStore:
    """Process-local ring buffer of completed runs (newest last)."""

    def __init__(self, max_runs: int) -> None:
        self._runs: deque[EvaluationRun] = deque(maxlen=max_runs)

    def add(self, run: EvaluationRun) -> None:
        self._runs.append(run)

    def all(self) -> list[EvaluationRun]:
        return list(self._runs)

    def get(self, run_id: str) -> EvaluationRun | None:
        return next((r for r in self._runs if r.run_id == run_id), None)

    def latest_by_type(self) -> dict[str, EvaluationRun]:
        latest: dict[str, EvaluationRun] = {}
        for r in self._runs:  # insertion order → last wins
            latest[r.retrieval_type] = r
        return latest

    def clear(self) -> None:
        self._runs.clear()


_STORE = EvaluationStore(settings.evaluation_max_stored_runs)


def get_store() -> EvaluationStore:
    return _STORE


class EvaluationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        query_embedder: QueryEmbedder | None = None,
        store: EvaluationStore | None = None,
    ) -> None:
        self.session = session
        self.store = store or get_store()
        self.vector = VectorSearchService(session, query_embedder=query_embedder)
        self.hybrid = HybridRetrievalService(session, query_embedder=query_embedder)

    # ---- DB-backed denominators ---------------------------------------------

    async def corpus_size(self) -> int:
        return int(
            await self.session.scalar(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.embedding.is_not(None)
                )
            )
            or 0
        )

    async def _total_relevant(self, ex: GroundTruthExample) -> int:
        if ex.expected_chunk_ids:
            return len(ex.expected_chunk_ids)
        if ex.expected_sections:
            conds = or_(
                *[
                    DocumentChunk.chunk_metadata.contains({"normalized_section_name": s})
                    for s in ex.expected_sections
                ]
            )
            return int(
                await self.session.scalar(
                    select(func.count(DocumentChunk.id)).where(
                        DocumentChunk.embedding.is_not(None), conds
                    )
                )
                or 0
            )
        if ex.expected_report_ids:
            return int(
                await self.session.scalar(
                    select(func.count(DocumentChunk.id)).where(
                        DocumentChunk.embedding.is_not(None),
                        DocumentChunk.report_id.in_(ex.expected_report_ids),
                    )
                )
                or 0
            )
        return 0

    # ---- retrieval strategies as runner callables ---------------------------

    async def _retrieve_vector(self, ex: GroundTruthExample, top_k: int) -> RetrievalOutput:
        try:
            outcome = await self.vector.search(ex.query, top_k=top_k)
        except SearchError as exc:
            return RetrievalOutput(results=[], candidate_count=0, latency_ms=0.0, error=str(exc))
        # Pure vector search considers the whole embedded corpus (no reduction).
        return RetrievalOutput(
            results=outcome.results,
            candidate_count=await self.corpus_size(),
            latency_ms=outcome.timings.total_ms,
        )

    async def _retrieve_hybrid(self, ex: GroundTruthExample, top_k: int) -> RetrievalOutput:
        ctx = RetrievalContext(**ex.filters) if ex.filters else RetrievalContext()
        try:
            outcome = await self.hybrid.run(ex.query, ctx, top_k=top_k, profile=ex.profile)
        except SearchError as exc:
            return RetrievalOutput(results=[], candidate_count=0, latency_ms=0.0, error=str(exc))
        return RetrievalOutput(
            results=outcome.results,
            candidate_count=outcome.candidate_count,
            latency_ms=outcome.timings.total_ms,
        )

    # ---- public API ----------------------------------------------------------

    async def run(
        self, *, retrieval_type: str = "both", top_k: int | None = None
    ) -> list[EvaluationRun]:
        k = top_k or settings.evaluation_default_top_k
        types = VALID_TYPES if retrieval_type == "both" else (retrieval_type,)
        examples = get_ground_truth()
        corpus = await self.corpus_size()

        runs: list[EvaluationRun] = []
        for rtype in types:
            retrieve = self._retrieve_vector if rtype == "vector" else self._retrieve_hybrid
            runner = BenchmarkRunner(retrieval_type=rtype, corpus_size=corpus)
            run = await runner.run(examples, retrieve, self._total_relevant, top_k=k)
            self.store.add(run)
            runs.append(run)
            log.info(
                "evaluation.run",
                retrieval_type=rtype,
                top_k=k,
                queries=run.num_queries,
                recall=run.mean_recall_at_k,
                precision=run.mean_precision_at_k,
                mrr=run.mean_mrr,
                hit_rate=run.hit_rate,
            )
        return runs
