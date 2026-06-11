"""Citation system builder for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations

import uuid
from typing import Any
from app.memo.memo_models import CitationSchema, MemoPackage


class CitationBuilder:
    """Matches and validates citations in generated memo sections back to the MemoPackage."""

    def __init__(self, package: MemoPackage):
        self.package = package
        # Pre-index package elements for fast lookup
        self.chunks_by_id = {c.id: c for c in package.retrieved_evidence}
        self.risks_by_id = {r.id: r for r in package.risks}

    def resolve_and_validate(self, raw_citations: list[dict[str, Any]]) -> list[CitationSchema]:
        """Resolves list of raw citations from LLM, validating and matching them against package sources."""
        resolved = []
        for raw in raw_citations:
            source_type = raw.get("source_type", "text_chunk").lower()
            ref_id_str = raw.get("chunk_id") or raw.get("ref_id")
            
            ref_id = None
            if ref_id_str:
                try:
                    ref_id = uuid.UUID(str(ref_id_str))
                except ValueError:
                    pass

            # Initialize schema fields
            report_id = self.package.report_id
            chunk_id = None
            page_number = raw.get("page_number")
            section_name = raw.get("section_name")
            text_snippet = raw.get("text_snippet")

            if source_type == "text_chunk" and ref_id and ref_id in self.chunks_by_id:
                chunk = self.chunks_by_id[ref_id]
                chunk_id = chunk.id
                page_number = chunk.page_number
                section_name = chunk.section_name
                text_snippet = text_snippet or chunk.content[:200]
            elif source_type == "risk_factor" and ref_id and ref_id in self.risks_by_id:
                risk = self.risks_by_id[ref_id]
                chunk_id = risk.source_chunk_id
                page_number = risk.page_number
                text_snippet = text_snippet or risk.description[:200]
                section_name = section_name or "Risk Factors"
            elif source_type == "financial_metric":
                # Metric citations match by metric name or standard metadata
                metric_name = raw.get("metric_name") or raw.get("text_snippet")
                # Try to find metric chunk
                text_snippet = text_snippet or f"Financial Metric: {metric_name}"
                section_name = section_name or "Financials"
            else:
                # Fallback: Jaccard similarity search over chunks if raw text snippet is provided
                if text_snippet and self.package.retrieved_evidence:
                    best_chunk = self._find_best_jaccard_match(text_snippet)
                    if best_chunk:
                        chunk_id = best_chunk.id
                        page_number = best_chunk.page_number
                        section_name = best_chunk.section_name
                        source_type = "text_chunk"

            resolved.append(
                CitationSchema(
                    report_id=report_id,
                    chunk_id=chunk_id,
                    page_number=page_number,
                    section_name=section_name,
                    source_type=source_type,
                    text_snippet=text_snippet
                )
            )
        return resolved

    def _find_best_jaccard_match(self, query: str) -> Any | None:
        """Finds the chunk with highest word-level Jaccard overlap with the query text."""
        query_words = set(query.lower().split())
        if not query_words:
            return None

        best_score = 0.0
        best_chunk = None

        for chunk in self.package.retrieved_evidence:
            chunk_words = set(chunk.content.lower().split())
            intersection = query_words.intersection(chunk_words)
            union = query_words.union(chunk_words)
            if not union:
                continue
            score = len(intersection) / len(union)
            if score > best_score:
                best_score = score
                best_chunk = chunk

        # Return best match if overlap is reasonable (> 0.05)
        return best_chunk if best_score > 0.05 else None
