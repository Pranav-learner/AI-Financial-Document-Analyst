"""Unit tests for Phase 6 Advanced Retrieval & RAG pipeline."""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.query_rewriting.models import QueryClass
from app.rag.query_rewriting.query_classifier import FinancialQueryClassifier
from app.rag.query_rewriting.query_rewriter import QueryRewriter
from app.rag.query_rewriting.validators import validate_query
from app.rag.query_rewriting.exceptions import QueryValidationError
from app.rag.hyde.hyde_generator import HyDEGenerator
from app.rag.hyde.hyde_service import HyDEService
from app.rag.reranking.reranker import BGEReranker
from app.rag.reranking.rerank_service import RerankService
from app.rag.context.token_budgeter import TokenBudgeter
from app.rag.context.citation_builder import CitationBuilder
from app.rag.context.context_ranker import ContextRanker
from app.rag.context.context_builder import ContextBuilder
from app.rag.service import AdvancedRAGService
from app.retrieval.hybrid import RetrievalContext
from app.retrieval.search.retrieval_models import SearchResult, SearchTimings


@pytest.mark.unit
def test_query_validator() -> None:
    # Should accept valid queries
    assert validate_query("What is the revenue growth?") == "What is the revenue growth?"
    
    # Should reject too long queries
    with pytest.raises(QueryValidationError, match="Query exceeds maximum length"):
        validate_query("a" * 8193)

    # Should reject too short queries
    with pytest.raises(QueryValidationError, match="Query must not be empty"):
        validate_query("")


@pytest.mark.unit
def test_query_classifier_local_rules() -> None:
    classifier = FinancialQueryClassifier(client=None)
    
    # Financial indicators
    assert classifier._classify_local("What is the gross margin?").predicted_class == QueryClass.FINANCIAL_METRIC
    assert classifier._classify_local("Show me revenue for Q3").predicted_class == QueryClass.FINANCIAL_METRIC
    
    # Risk indicators
    assert classifier._classify_local("What are the risk factors?").predicted_class == QueryClass.RISK
    assert classifier._classify_local("Any regulatory litigations?").predicted_class == QueryClass.RISK
    
    # Tone indicators
    assert classifier._classify_local("How positive is the management tone?").predicted_class == QueryClass.TONE
    
    # Guidance indicators
    assert classifier._classify_local("What is the forecast for next year?").predicted_class == QueryClass.GUIDANCE
    
    # Default fallback
    assert classifier._classify_local("Tell me about the CEO history").predicted_class == QueryClass.GENERAL


@pytest.mark.unit
def test_query_rewriter_fallback() -> None:
    rewriter = QueryRewriter(client=None)
    
    # Financial metrics rewriting
    metrics_query = "What is the revenue growth?"
    res = rewriter.rewrite(metrics_query)
    assert res.original_query == metrics_query
    assert len(res.rewritten_query) > 0
    assert res.query_class == QueryClass.FINANCIAL_METRIC
    
    # General queries
    general_query = "Who is the CEO?"
    res_general = rewriter.rewrite(general_query)
    assert res_general.original_query == general_query
    assert res_general.query_class == QueryClass.GENERAL


@pytest.mark.unit
def test_hyde_generator_fallback() -> None:
    generator = HyDEGenerator(client=None)
    
    res = generator.generate("What is the gross margin?")
    assert len(res.hypothetical_document) > 0
    assert "gross margin" in res.hypothetical_document.lower() or "revenue" in res.hypothetical_document.lower()


@pytest.mark.unit
def test_bge_reranker_fallback() -> None:
    reranker = BGEReranker()
    
    doc1 = "The company reported high revenue growth and increased market share."
    doc2 = "Random unrelated text about corporate governance policies."
    query = "revenue growth"
    
    scores = reranker.compute_scores(query, [doc1, doc2])
    assert len(scores) == 2
    assert scores[0] > scores[1]  # Doc 1 has terms matching query, Doc 2 does not


@pytest.mark.unit
def test_token_budgeter() -> None:
    budgeter_small = TokenBudgeter(size="SMALL")
    assert budgeter_small.limit == 4000
    
    budgeter_med = TokenBudgeter(size="MEDIUM")
    assert budgeter_med.limit == 16000
    
    budgeter_large = TokenBudgeter(size="LARGE")
    assert budgeter_large.limit == 64000


@pytest.mark.unit
def test_citation_builder() -> None:
    builder = CitationBuilder()
    
    report_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    
    # Build search result
    res = SearchResult(
        chunk_id=chunk_id,
        report_id=report_id,
        section_id=None,
        score=0.9,
        chunk_text="This is a preview",
        metadata={"start_page": 12, "section_name": "MD&A"}
    )
    
    # Build citation
    citation = builder.build_citation(res)
    
    assert citation.citation_id == 1
    assert citation.page_number == 12
    assert citation.section_name == "MD&A"
    
    # Retrieve same citation -> should return cached entry
    citation2 = builder.build_citation(res)
    assert citation2.citation_id == 1
    assert len(builder.get_citations_list()) == 1


@pytest.mark.unit
def test_context_ranker() -> None:
    ranker = ContextRanker()
    
    r1 = SearchResult(
        chunk_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        section_id=None,
        score=0.9,
        chunk_text="text 1",
        metadata={"fiscal_year": 2023}
    )
    r2 = SearchResult(
        chunk_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        section_id=None,
        score=0.8,
        chunk_text="text 2",
        metadata={"fiscal_year": 2024}
    )
    
    # Rank by relevance (score desc)
    relevance_sorted = ranker.sort_chunks(list([r2, r1]))
    assert relevance_sorted[0].score == 0.9
    assert relevance_sorted[0].metadata["fiscal_year"] == 2023
    assert relevance_sorted[1].metadata["fiscal_year"] == 2024


@pytest.mark.unit
def test_context_builder() -> None:
    r1 = SearchResult(
        chunk_id=uuid.uuid4(),
        report_id=uuid.uuid4(),
        section_id=None,
        score=0.9,
        chunk_text="The company's gross margin was 45%.",
        metadata={"company_name": "Tesla", "fiscal_year": 2023, "fiscal_period": "FY", "start_page": 5, "section_name": "MD&A"}
    )
    
    builder = ContextBuilder(budget_size="SMALL")
    pkg = builder.build([r1])
    
    assert pkg.tokens_used > 0
    assert pkg.budget_limit == 4000
    assert len(pkg.citations) == 1
    assert "gross margin was 45%" in pkg.context_text
    assert "<evidence id=\"1\"" in pkg.context_text
    assert "</evidence>" in pkg.context_text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_advanced_rag_service_flow() -> None:
    # Set up mock dependencies
    mock_session = MagicMock()
    mock_query_embedder = MagicMock()
    
    # Create test search results
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    mock_results = [
        SearchResult(
            chunk_id=chunk_id,
            report_id=doc_id,
            section_id=None,
            score=0.95,
            chunk_text="Mock financial performance details.",
            metadata={"company_name": "Acme", "fiscal_year": 2024, "start_page": 1, "section_name": "MD&A"}
        )
    ]
    
    mock_outcome = MagicMock()
    mock_outcome.results = mock_results
    mock_outcome.candidate_count = 1
    mock_outcome.timings = MagicMock()
    mock_outcome.timings.as_dict = MagicMock(return_value={"total_ms": 2.0})
    
    # Patch the HybridRetrievalService inside AdvancedRAGService
    with patch("app.rag.service.HybridRetrievalService") as mock_hybrid_class:
        mock_hybrid_instance = MagicMock()
        mock_hybrid_instance.run = AsyncMock(return_value=mock_outcome)
        mock_hybrid_class.return_value = mock_hybrid_instance
        
        # Initialize service
        service = AdvancedRAGService(mock_session, query_embedder=mock_query_embedder)
        
        ctx = RetrievalContext()
        context_pkg, steps, re_ranked_results, pre_rerank_results = await service.retrieve_and_assemble(
            query="Acme gross margin",
            context=ctx,
            strategy="FINANCIAL_METRICS",
            top_k=5
        )
        
        # Verify orchestration calls
        assert context_pkg.tokens_used > 0
        assert len(context_pkg.citations) == 1
        assert context_pkg.citations[0].chunk_id == chunk_id
        assert len(re_ranked_results) == 1
        assert re_ranked_results[0].score > 0.0
        
        # Verify steps trace contents
        assert "resolved_strategy" in steps
        assert steps["resolved_strategy"] == "FINANCIAL_METRICS"
        assert "query_rewriting" in steps
        assert "retrieval" in steps
        assert "reranking" in steps
