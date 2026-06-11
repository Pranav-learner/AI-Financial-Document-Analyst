"""RAG context builder engine (Phase 6)."""

from __future__ import annotations

import uuid
from app.core.logging import get_logger
from app.rag.context.models import ContextPackage
from app.rag.context.citation_builder import CitationBuilder
from app.rag.context.context_ranker import ContextRanker
from app.rag.context.token_budgeter import TokenBudgeter, BudgetSize
from app.retrieval.search.retrieval_models import SearchResult

log = get_logger(__name__)


class ContextBuilder:
    """Builds the grounded context package with deduplication, token limits, and XML format."""

    def __init__(
        self,
        *,
        budget_size: BudgetSize | str = BudgetSize.SMALL,
        ranker: ContextRanker | None = None,
        token_budgeter: TokenBudgeter | None = None
    ) -> None:
        self.ranker = ranker or ContextRanker()
        self.budgeter = token_budgeter or TokenBudgeter(budget_size)
        self.citation_builder = CitationBuilder()

    def build(self, results: list[SearchResult]) -> ContextPackage:
        # 1. Deduplicate chunks by chunk_id
        seen_ids = set()
        deduped = []
        for r in results:
            cid = str(r.chunk_id)
            if cid not in seen_ids:
                seen_ids.add(cid)
                deduped.append(r)

        # 2. Sort/Rank chunks
        ranked = self.ranker.sort_chunks(deduped)

        # 3. Fit to token budget
        admitted = self.budgeter.fit_chunks(ranked)

        # 4. Serialize with citations
        context_blocks = []
        for res in admitted:
            # Build citation
            cit = self.citation_builder.build_citation(res)

            meta = res.metadata or {}
            sec_name = meta.get("normalized_section_name") or meta.get("section_name") or "Unknown Section"
            page_num = meta.get("start_page") or meta.get("page_number") or "Unknown"

            # Create XML evidence tag
            block = (
                f"<evidence id=\"{cit.citation_id}\" report_id=\"{res.report_id}\" "
                f"page=\"{page_num}\" section=\"{sec_name}\">\n"
                f"{res.chunk_text.strip()}\n"
                f"</evidence>"
            )
            context_blocks.append(block)

        context_text = "\n\n".join(context_blocks)
        tokens_used = self.budgeter.count_tokens(context_text)

        log.info(
            "context_builder.built",
            chunks_admitted=len(admitted),
            tokens_used=tokens_used,
            limit=self.budgeter.limit
        )

        return ContextPackage(
            context_text=context_text,
            tokens_used=tokens_used,
            budget_limit=self.budgeter.limit,
            citations=self.citation_builder.get_citations_list()
        )
