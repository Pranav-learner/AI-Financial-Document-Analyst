"""Citation generation and formatting (Phase 6)."""

from __future__ import annotations

import uuid
from app.rag.context.models import Citation
from app.retrieval.search.retrieval_models import SearchResult


class CitationBuilder:
    """Generates traceable citations for retrieved document chunks."""

    def __init__(self) -> None:
        self.citations: dict[uuid.UUID, Citation] = {}
        self._next_id = 1

    def build_citation(self, res: SearchResult) -> Citation:
        chunk_uuid = res.chunk_id if isinstance(res.chunk_id, uuid.UUID) else uuid.UUID(str(res.chunk_id))

        if chunk_uuid in self.citations:
            return self.citations[chunk_uuid]

        report_uuid = res.report_id if isinstance(res.report_id, uuid.UUID) else uuid.UUID(str(res.report_id))

        meta = res.metadata or {}
        # Fetch page number (either start_page, or page_number if it exists)
        page_num = meta.get("start_page") or meta.get("page_number")
        if page_num is not None:
            try:
                page_num = int(page_num)
            except (ValueError, TypeError):
                page_num = None

        section_name = meta.get("normalized_section_name") or meta.get("section_name")

        citation = Citation(
            citation_id=self._next_id,
            report_id=report_uuid,
            chunk_id=chunk_uuid,
            page_number=page_num,
            section_name=section_name,
            source_text_preview=res.chunk_text[:120].strip() + "..."
        )
        self.citations[chunk_uuid] = citation
        self._next_id += 1
        return citation

    def get_citations_list(self) -> list[Citation]:
        return list(self.citations.values())
