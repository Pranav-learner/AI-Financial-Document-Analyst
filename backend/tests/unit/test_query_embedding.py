"""Unit tests for the query embedding pipeline (Phase 2B)."""

from __future__ import annotations

import pytest
from app.retrieval.embeddings.exceptions import RateLimitError
from app.retrieval.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.retrieval.embeddings.provider import EmbeddingProvider
from app.retrieval.search.query_embedding import QueryEmbedder
from app.retrieval.search.search_exceptions import (
    EmptyQueryError,
    QueryEmbeddingError,
    QueryTooLongError,
)

DIM = 4


class FakeProvider(EmbeddingProvider):
    def __init__(self, *, vector=None, raises=None) -> None:
        self._vector = vector if vector is not None else [0.5] * DIM
        self._raises = raises

    @property
    def model_name(self) -> str:
        return "fake-model"

    @property
    def dimension(self) -> int:
        return DIM

    def embed_documents(self, texts):
        if self._raises:
            raise self._raises
        return [list(self._vector) for _ in texts]


@pytest.mark.unit
def test_valid_query_returns_vector_and_stats() -> None:
    qe = QueryEmbedder(FakeProvider(), expected_dim=DIM)
    vec, stats = qe.embed("supply chain risk")
    assert len(vec) == DIM
    assert stats.dimension == DIM
    assert stats.model == "fake-model"
    assert stats.task_type  # populated from settings
    assert len(stats.preview) <= 5


@pytest.mark.unit
def test_empty_query_raises() -> None:
    qe = QueryEmbedder(FakeProvider(), expected_dim=DIM)
    with pytest.raises(EmptyQueryError):
        qe.embed("")
    with pytest.raises(EmptyQueryError):
        qe.embed("   ")


@pytest.mark.unit
def test_too_long_query_raises() -> None:
    qe = QueryEmbedder(FakeProvider(), expected_dim=DIM)
    with pytest.raises(QueryTooLongError):
        qe.embed("x" * 100_000)


@pytest.mark.unit
def test_provider_error_becomes_query_embedding_error() -> None:
    qe = QueryEmbedder(FakeProvider(raises=RateLimitError("429")), expected_dim=DIM)
    with pytest.raises(QueryEmbeddingError):
        qe.embed("cash flow")


@pytest.mark.unit
def test_wrong_dimension_raises() -> None:
    qe = QueryEmbedder(FakeProvider(vector=[0.1] * (DIM + 3)), expected_dim=DIM)
    with pytest.raises(QueryEmbeddingError):
        qe.embed("revenue growth")


@pytest.mark.unit
def test_gemini_embed_query_uses_query_task_type() -> None:
    captured = {}

    class _P(GeminiEmbeddingProvider):
        def _embed_once(self, texts, task_type=None):
            captured["task_type"] = task_type
            return [[0.3] * DIM for _ in texts]

    p = _P(
        api_key="x",
        model="gemini-embedding-001",
        dimension=DIM,
        task_type="RETRIEVAL_DOCUMENT",
        query_task_type="RETRIEVAL_QUERY",
        client=object(),
        sleep=lambda _d: None,
    )
    p.embed_query("a query")
    assert captured["task_type"] == "RETRIEVAL_QUERY"
    # and documents still use the document task type
    p.embed_documents(["a doc"])
    assert captured["task_type"] == "RETRIEVAL_DOCUMENT"
