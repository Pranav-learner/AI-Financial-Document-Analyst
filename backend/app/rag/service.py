"""Advanced RAG retrieval service orchestrator (Phase 6)."""

from __future__ import annotations

import time
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.rag.query_rewriting.query_rewriter import QueryRewriter
from app.rag.hyde.hyde_service import HyDEService
from app.rag.reranking.rerank_service import RerankService
from app.rag.context.context_builder import ContextBuilder
from app.rag.strategy import get_strategy_config, RetrievalStrategy
from app.retrieval.hybrid import HybridRetrievalService, RetrievalContext
from app.retrieval.search.query_embedding import QueryEmbedder
from app.retrieval.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.rag.context.models import ContextPackage

log = get_logger(__name__)


class AdvancedRAGService:
    """Orchestrates query understanding, rewriting, HyDE, hybrid search, reranking, and context assembly."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        query_embedder: QueryEmbedder | None = None,
        query_rewriter: QueryRewriter | None = None,
        hyde_service: HyDEService | None = None,
        rerank_service: RerankService | None = None,
    ) -> None:
        self.session = session
        provider = GeminiEmbeddingProvider.from_settings()
        self.query_embedder = query_embedder or QueryEmbedder(provider)
        self.hybrid_service = HybridRetrievalService(session, query_embedder=self.query_embedder)

        self.query_rewriter = query_rewriter or QueryRewriter(client=None)
        self.hyde_service = hyde_service or HyDEService(self.query_embedder)
        self.rerank_service = rerank_service or RerankService()

    async def retrieve_and_assemble(
        self,
        query: str,
        context: RetrievalContext,
        *,
        strategy: RetrievalStrategy | str | None = None,
        top_k: int | None = None,
    ) -> tuple[ContextPackage, dict]:
        """Orchestrate advanced retrieval pipeline."""
        t_start = time.monotonic()
        steps = {}
        original_query = query.strip()

        # 1. Resolve strategy config
        strat_config = get_strategy_config(strategy)
        steps["resolved_strategy"] = strategy or "GENERAL_ANALYSIS"
        steps["strategy_config"] = strat_config.model_dump()

        # 2. Query Rewriting & Classification
        rewritten_query = original_query
        sub_queries = [original_query]
        keywords = []
        q_class = "GENERAL"

        if strat_config.query_rewriting:
            t0 = time.monotonic()
            rewrite_res = self.query_rewriter.rewrite(original_query)
            rewritten_query = rewrite_res.rewritten_query
            sub_queries = rewrite_res.sub_queries if rewrite_res.sub_queries else [original_query]
            keywords = rewrite_res.keywords
            q_class = rewrite_res.query_class.value
            steps["query_rewriting"] = {
                "original_query": original_query,
                "rewritten_query": rewritten_query,
                "sub_queries": sub_queries,
                "keywords": keywords,
                "query_class": q_class,
                "duration_ms": round((time.monotonic() - t0) * 1000, 2)
            }
        else:
            steps["query_rewriting"] = {
                "original_query": original_query,
                "rewritten_query": original_query,
                "sub_queries": [original_query],
                "keywords": [],
                "query_class": "GENERAL",
                "duration_ms": 0.0
            }

        # 3. HyDE hypothetical document generation
        hyde_document = None
        retrieval_query = rewritten_query
        if strat_config.hyde:
            t0 = time.monotonic()
            # Generate HyDE result
            hyde_res = self.hyde_service.generator.generate(rewritten_query)
            hyde_document = hyde_res.hypothetical_document
            retrieval_query = hyde_document  # Retrieve using HyDE doc instead of rewritten query
            steps["hyde"] = {
                "query_input": rewritten_query,
                "hypothetical_document": hyde_document,
                "duration_ms": round((time.monotonic() - t0) * 1000, 2)
            }
        else:
            steps["hyde"] = {
                "query_input": rewritten_query,
                "hypothetical_document": None,
                "duration_ms": 0.0
            }

        # 4. Multi-query Hybrid Retrieval
        # We retrieve separately for each sub-query, then merge the results by chunk ID (keeping highest score)
        t0 = time.monotonic()
        depth = strat_config.retrieval_depth

        merged_results_map = {}
        retrieval_queries = []
        if strat_config.hyde:
            # If HyDE is enabled, we search using the single hypothetical document
            retrieval_queries = [retrieval_query]
        else:
            # Else, we search using the generated sub-queries
            retrieval_queries = sub_queries

        search_steps = []
        for q in retrieval_queries:
            outcome = await self.hybrid_service.run(
                query=q,
                context=context,
                top_k=depth,
                profile=steps["resolved_strategy"]
            )
            search_steps.append({
                "query": q,
                "returned_count": len(outcome.results),
                "candidate_count": outcome.candidate_count,
                "timings": outcome.timings.as_dict()
            })
            for res in outcome.results:
                cid = str(res.chunk_id)
                if cid not in merged_results_map or res.score > merged_results_map[cid].score:
                    merged_results_map[cid] = res

        retrieved_results = list(merged_results_map.values())
        steps["retrieval"] = {
            "queries_executed": retrieval_queries,
            "total_retrieved_before_dedup": sum(s["returned_count"] for s in search_steps),
            "merged_count": len(retrieved_results),
            "search_steps": search_steps,
            "duration_ms": round((time.monotonic() - t0) * 1000, 2)
        }

        # 5. Re-ranking
        re_ranked_results = retrieved_results
        k = top_k or strat_config.retrieval_depth
        # Limit target K bounds to sensible defaults
        k = max(5, min(k, 50))

        if strat_config.reranking and retrieved_results:
            t0 = time.monotonic()
            re_ranked_results = self.rerank_service.rerank(
                original_query,
                retrieved_results,
                top_k=k
            )
            steps["reranking"] = {
                "candidates_count": len(retrieved_results),
                "returned_count": len(re_ranked_results),
                "duration_ms": round((time.monotonic() - t0) * 1000, 2)
            }
        else:
            # Sort by original score and limit to K
            re_ranked_results = sorted(retrieved_results, key=lambda r: r.score, reverse=True)[:k]
            steps["reranking"] = {
                "candidates_count": len(retrieved_results),
                "returned_count": len(re_ranked_results),
                "duration_ms": 0.0
            }

        # 6. Context Assembly
        t0 = time.monotonic()
        context_builder = ContextBuilder(budget_size=strat_config.context_size)
        context_package = context_builder.build(re_ranked_results)
        steps["context_assembly"] = {
            "tokens_used": context_package.tokens_used,
            "budget_limit": context_package.budget_limit,
            "citations_count": len(context_package.citations),
            "duration_ms": round((time.monotonic() - t0) * 1000, 2)
        }

        steps["total_pipeline_ms"] = round((time.monotonic() - t_start) * 1000, 2)

        return context_package, steps, re_ranked_results, retrieved_results
