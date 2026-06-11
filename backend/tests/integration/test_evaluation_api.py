"""Integration tests for Phase 2D: query → retrieval → evaluation → metrics.

Seeds a corpus whose sections/text line up with the packaged benchmark suite,
runs the real EvaluationService (vector + hybrid) with a deterministic hashing
embedder, and checks the metrics, the dashboard APIs, and the vector-vs-hybrid
comparison — all against a live PostgreSQL, no Gemini key/network.
"""

from __future__ import annotations

import hashlib
import math
import re

import pytest
from app.api.v1.endpoints.evaluation import get_evaluation_service
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.document_chunk import DocumentChunk
from app.models.enums import EmbeddingStatus, ReportStatus
from app.models.report import Report
from app.retrieval.embeddings.provider import EmbeddingProvider
from app.retrieval.evaluation import EvaluationService, get_store
from app.retrieval.search import QueryEmbedder
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

PREFIX = settings.api_v1_prefix
DIM = settings.embedding_dim


class HashingProvider(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return "hashing-test"

    @property
    def dimension(self) -> int:
        return DIM

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    @staticmethod
    def _vec(text: str) -> list[float]:
        v = [0.0] * DIM
        for tok in re.findall(r"[a-z0-9]+", text.lower()):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


@pytest.fixture
def eval_client(api_client: AsyncClient) -> AsyncClient:
    async def _override(db: AsyncSession = Depends(get_db)) -> EvaluationService:
        return EvaluationService(db, query_embedder=QueryEmbedder(HashingProvider()))

    get_store().clear()
    app.dependency_overrides[get_evaluation_service] = _override
    yield api_client
    app.dependency_overrides.pop(get_evaluation_service, None)
    get_store().clear()


# section -> representative text aligned to the benchmark queries
_CORPUS = {
    "Risk Factors": "supply chain disruption risk and cybersecurity data breach risk to operations",
    "Income Statement": "operating margin gross margin revenue net income earnings per share",
    "Cash Flow Statement": "cash flow from operations capital expenditure investing financing activities",
    "Forward Guidance": "future outlook and forward guidance for next fiscal year revenue expectations",
    "MD&A": "management discussion and analysis of results operating margin and liquidity",
    "Management Commentary": "management commentary on quarterly performance results and strategy",
    "Business Overview": "company business overview of products markets and operations",
    "Legal Proceedings": "ordinary course litigation and regulatory matters unrelated noise",
}


def _seed(session: Session) -> None:
    report = Report(
        report_type="10-K", year=2024, original_filename="x.pdf",
        storage_path="reports/2026/06/x.pdf", status=ReportStatus.EMBEDDED, total_pages=1,
    )
    session.add(report)
    session.commit()
    for idx, (section, text) in enumerate(_CORPUS.items()):
        session.add(
            DocumentChunk(
                report_id=report.id, chunk_index=idx, chunk_text=text,
                token_count=len(text.split()),
                chunk_metadata={"normalized_section_name": section, "report_id": str(report.id)},
                embedding=HashingProvider._vec(text),
                embedding_status=EmbeddingStatus.COMPLETED.value, embedding_model="hashing-test",
            )
        )
    session.commit()


@pytest.mark.integration
async def test_benchmarks_endpoint(eval_client: AsyncClient) -> None:
    resp = await eval_client.get(f"{PREFIX}/evaluation/benchmarks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 9
    assert "RISK" in body["categories"]
    assert all("expected_sections" in e for e in body["examples"])


@pytest.mark.integration
async def test_run_evaluation_both_and_metrics(
    eval_client: AsyncClient, sync_session: Session
) -> None:
    _seed(sync_session)
    resp = await eval_client.post(
        f"{PREFIX}/evaluation/run", json={"retrieval_type": "both", "top_k": 10}
    )
    assert resp.status_code == 200, resp.text
    runs = resp.json()["runs"]
    assert {r["retrieval_type"] for r in runs} == {"vector", "hybrid"}
    for r in runs:
        assert r["num_queries"] == 9
        assert r["failures"] == 0
        assert 0.0 <= r["mean_recall_at_k"] <= 1.0
        assert r["results"]              # per-query detail present
        assert all("recall_at_k" in q and "mrr" in q for q in r["results"])

    vector = next(r for r in runs if r["retrieval_type"] == "vector")
    hybrid = next(r for r in runs if r["retrieval_type"] == "hybrid")
    # Vector retrieves relevant content; hybrid filters → candidate reduction.
    assert vector["mean_recall_at_k"] > 0.0
    assert vector["mean_candidate_reduction_pct"] == 0.0
    assert hybrid["mean_candidate_reduction_pct"] > 0.0
    # Filtering removes off-section noise → hybrid precision ≥ vector precision.
    assert hybrid["mean_precision_at_k"] >= vector["mean_precision_at_k"]


@pytest.mark.integration
async def test_results_and_comparison_apis(
    eval_client: AsyncClient, sync_session: Session
) -> None:
    _seed(sync_session)
    await eval_client.post(f"{PREFIX}/evaluation/run", json={"retrieval_type": "both"})

    results = (await eval_client.get(f"{PREFIX}/evaluation/results")).json()
    assert results["count"] >= 2

    metrics = (await eval_client.get(f"{PREFIX}/evaluation/metrics")).json()
    assert "vector" in metrics["latest"] and "hybrid" in metrics["latest"]
    assert metrics["comparison"] is not None
    assert metrics["comparison"]["hybrid_candidate_reduction_pct"] > 0.0


@pytest.mark.integration
async def test_single_strategy_run(eval_client: AsyncClient, sync_session: Session) -> None:
    _seed(sync_session)
    resp = await eval_client.post(
        f"{PREFIX}/evaluation/run", json={"retrieval_type": "vector", "top_k": 5}
    )
    runs = resp.json()["runs"]
    assert len(runs) == 1 and runs[0]["retrieval_type"] == "vector"
    assert runs[0]["top_k"] == 5


@pytest.mark.integration
async def test_invalid_retrieval_type_is_422(eval_client: AsyncClient) -> None:
    resp = await eval_client.post(
        f"{PREFIX}/evaluation/run", json={"retrieval_type": "magic"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_EVALUATION_REQUEST"


@pytest.mark.integration
async def test_ranking_correctness_cash_flow(
    eval_client: AsyncClient, sync_session: Session
) -> None:
    """The 'cash flow' benchmark query must score the Cash Flow Statement chunk relevant."""
    _seed(sync_session)
    resp = await eval_client.post(
        f"{PREFIX}/evaluation/run", json={"retrieval_type": "hybrid", "top_k": 10}
    )
    hybrid = resp.json()["runs"][0]
    cash = next(q for q in hybrid["results"] if q["query"] == "cash flow")
    assert cash["recall_at_k"] > 0.0 and cash["hit_rate"] == 1.0
