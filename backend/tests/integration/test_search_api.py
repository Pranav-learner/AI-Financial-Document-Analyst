"""Integration tests for Phase 2B: query → embedding → pgvector search → results.

A deterministic **token-hashing** embedder is used for BOTH stored chunks and
queries (a shared vector space), so retrieval-quality checks are real and
reproducible with no Gemini key/network — while the real `VectorSearchService`,
`VectorSearch`, pgvector cosine KNN, and the FastAPI endpoints are exercised
against a live PostgreSQL.
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid

import pytest
from app.api.v1.endpoints.search import get_search_service
from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.document_chunk import DocumentChunk
from app.models.enums import EmbeddingStatus, ReportStatus
from app.models.report import Report
from app.retrieval.embeddings.provider import EmbeddingProvider
from app.retrieval.search import QueryEmbedder, VectorSearchService
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

PREFIX = settings.api_v1_prefix
DIM = settings.embedding_dim


class HashingProvider(EmbeddingProvider):
    """Deterministic bag-of-tokens embedder (shared doc/query space)."""

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
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM
            v[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]


@pytest.fixture
def search_client(api_client: AsyncClient) -> AsyncClient:
    """api_client + the search service overridden to use the hashing embedder."""

    async def _override(db: AsyncSession = Depends(get_db)) -> VectorSearchService:
        return VectorSearchService(db, query_embedder=QueryEmbedder(HashingProvider()))

    app.dependency_overrides[get_search_service] = _override
    yield api_client
    app.dependency_overrides.pop(get_search_service, None)


def _make_report(session: Session) -> uuid.UUID:
    report = Report(
        report_type="10-K", year=2025, original_filename="x.pdf",
        storage_path="reports/2026/06/x.pdf", status=ReportStatus.EMBEDDED, total_pages=1,
    )
    session.add(report)
    session.commit()
    return report.id


def _add_chunk(
    session: Session, report_id: uuid.UUID, idx: int, text: str, section: str,
    *, embed: bool = True,
) -> None:
    vec = HashingProvider._vec(text) if embed else None
    session.add(
        DocumentChunk(
            report_id=report_id,
            chunk_index=idx,
            chunk_text=text,
            token_count=len(text.split()),
            chunk_metadata={"normalized_section_name": section, "report_id": str(report_id)},
            embedding=vec,
            embedding_status=(
                EmbeddingStatus.COMPLETED.value if embed else EmbeddingStatus.PENDING.value
            ),
            embedding_model="hashing-test" if embed else None,
        )
    )
    session.commit()


# Distinctive section texts for retrieval-quality checks.
_CORPUS = [
    ("Cash Flow", "Net cash provided by operating activities. Cash flow from operations "
                  "was 3.1 billion dollars this fiscal year."),
    ("Risk Factors", "Supply chain disruption risk could materially affect our ability to "
                     "manufacture and deliver products on time."),
    ("MD&A", "Total revenue increased fourteen percent year over year driven by subscription "
             "growth and higher renewals."),
    ("Financial Statements", "Consolidated balance sheets present total assets liabilities "
                             "and shareholders equity."),
]


def _seed_corpus(session: Session) -> uuid.UUID:
    report_id = _make_report(session)
    for i, (section, text) in enumerate(_CORPUS):
        _add_chunk(session, report_id, i, text, section)
    return report_id


@pytest.mark.integration
async def test_vector_search_returns_topk_with_scores(
    search_client: AsyncClient, sync_session: Session
) -> None:
    _seed_corpus(sync_session)
    resp = await search_client.post(
        f"{PREFIX}/search/vector", json={"query": "cash flow from operations", "top_k": 5}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["top_k"] == 5
    assert body["count"] >= 1
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)          # ranked, no re-ranking
    assert all(-1.0001 <= s <= 1.0001 for s in scores)     # cosine similarity range
    first = body["results"][0]
    assert {"chunk_id", "report_id", "section_id", "score", "chunk_text", "metadata"} <= set(first)
    assert "timings" in body and body["timings"]["total_ms"] >= 0.0


@pytest.mark.integration
async def test_retrieval_quality_cash_flow(
    search_client: AsyncClient, sync_session: Session
) -> None:
    _seed_corpus(sync_session)
    resp = await search_client.post(
        f"{PREFIX}/search/vector", json={"query": "cash flow", "top_k": 5}
    )
    top = resp.json()["results"][0]
    assert top["metadata"]["normalized_section_name"] == "Cash Flow"


@pytest.mark.integration
async def test_retrieval_quality_supply_chain_risk(
    search_client: AsyncClient, sync_session: Session
) -> None:
    _seed_corpus(sync_session)
    resp = await search_client.post(
        f"{PREFIX}/search/vector", json={"query": "supply chain disruption risk", "top_k": 5}
    )
    top = resp.json()["results"][0]
    assert top["metadata"]["normalized_section_name"] == "Risk Factors"


@pytest.mark.integration
async def test_debug_endpoint_returns_embedding_stats(
    search_client: AsyncClient, sync_session: Session
) -> None:
    _seed_corpus(sync_session)
    resp = await search_client.post(
        f"{PREFIX}/search/debug", json={"query": "revenue growth", "top_k": 5}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query_embedding"]["dimension"] == DIM
    assert body["query_embedding"]["task_type"]
    assert math.isclose(body["query_embedding"]["norm"], 1.0, rel_tol=1e-3)
    assert "timings" in body and len(body["results"]) >= 1


@pytest.mark.integration
async def test_empty_query_is_rejected(search_client: AsyncClient) -> None:
    # "" fails Pydantic min_length; whitespace passes schema but the service rejects it.
    r1 = await search_client.post(f"{PREFIX}/search/vector", json={"query": "", "top_k": 10})
    assert r1.status_code == 422
    r2 = await search_client.post(f"{PREFIX}/search/vector", json={"query": "   ", "top_k": 10})
    assert r2.status_code == 422


@pytest.mark.integration
async def test_top_k_out_of_range_is_rejected(search_client: AsyncClient) -> None:
    for bad in (2, 100):
        resp = await search_client.post(
            f"{PREFIX}/search/vector", json={"query": "cash", "top_k": bad}
        )
        assert resp.status_code == 422, f"top_k={bad}"


@pytest.mark.integration
async def test_no_results_when_nothing_embedded(search_client: AsyncClient) -> None:
    # Empty DB → valid request, zero results (not an error).
    resp = await search_client.post(
        f"{PREFIX}/search/vector", json={"query": "anything", "top_k": 10}
    )
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.integration
async def test_null_embedding_chunks_excluded(
    search_client: AsyncClient, sync_session: Session
) -> None:
    report_id = _make_report(sync_session)
    _add_chunk(sync_session, report_id, 0, "cash flow from operations", "Cash Flow", embed=True)
    _add_chunk(sync_session, report_id, 1, "cash flow not yet embedded", "Cash Flow", embed=False)
    resp = await search_client.post(
        f"{PREFIX}/search/vector", json={"query": "cash flow", "top_k": 50}
    )
    body = resp.json()
    assert body["count"] == 1  # the un-embedded (NULL) chunk is excluded
