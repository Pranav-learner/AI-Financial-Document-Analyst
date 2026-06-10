"""Rule-based section detector (Phase 1B).

Deterministic, LLM-free. Scans page text for SEC item headings, transcript
markers, and known section headings (via the configurable taxonomy), assigns a
confidence tier per match, computes page boundaries, and returns whole-section
content. No chunking, embeddings, or model calls.

Boundary model: a section starts at the page of its detected heading and runs
until the page before the next detected section (or the last page).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.ingestion.section_detection.normalization import normalize_heading
from app.ingestion.section_detection.section_patterns import (
    PART_RE,
    is_mostly_uppercase,
    is_strong_heading,
    is_toc_line,
    iter_lines,
    match_sec_item,
)
from app.ingestion.section_detection.taxonomy import Taxonomy, get_taxonomy

log = get_logger(__name__)


@dataclass(frozen=True)
class DetectedSection:
    section_name: str
    normalized_section_name: str
    start_page: int
    end_page: int
    content: str
    confidence_score: float


@dataclass(frozen=True)
class _Hit:
    page_number: int
    offset: int
    raw_heading: str
    canonical: str
    confidence: float


class SectionDetector:
    def __init__(self, taxonomy: Taxonomy | None = None) -> None:
        self.tax = taxonomy or get_taxonomy()
        self._transcript_canonicals = set(self.tax.transcript_markers.values())

    # -- public ----------------------------------------------------------------

    def detect(
        self, pages: list[tuple[int, str]], report_type: str | None = None
    ) -> list[DetectedSection]:
        """Detect sections from (page_number, text) pairs."""
        if not pages:
            return []

        pages = sorted(pages, key=lambda p: p[0])
        page_text = {n: t for n, t in pages}
        first_page, last_page = pages[0][0], pages[-1][0]
        is_transcript = (report_type or "").upper() == "TRANSCRIPT"

        report_type = (report_type or "").upper()
        current_part = "I"  # SEC filings default to Part I until a PART marker flips it

        hits: list[_Hit] = []
        for page_number, text in pages:
            for offset, line in iter_lines(text):
                part_match = PART_RE.match(line)
                if part_match and not is_toc_line(line):
                    current_part = part_match.group(1).upper()
                    continue  # PART markers set context; they are not sections
                hit = self._match_line(
                    line, page_number, offset, is_transcript, report_type, current_part
                )
                if hit is not None:
                    hits.append(hit)

        if not hits:
            log.info("sections.none_detected", first_page=first_page, last_page=last_page)
            return [self._fallback_section(page_text, first_page, last_page)]

        # Keep the earliest occurrence per canonical section (the section start).
        hits.sort(key=lambda h: (h.page_number, h.offset))
        unique: list[_Hit] = []
        seen: set[str] = set()
        for h in hits:
            if h.canonical not in seen:
                seen.add(h.canonical)
                unique.append(h)
        unique.sort(key=lambda h: (h.page_number, h.offset))

        sections: list[DetectedSection] = []
        for i, h in enumerate(unique):
            start_page = h.page_number
            if i + 1 < len(unique):
                next_start = unique[i + 1].page_number
                end_page = next_start - 1 if next_start > start_page else start_page
            else:
                end_page = last_page
            end_page = max(end_page, start_page)

            content = self._content_for(page_text, start_page, end_page)
            sections.append(
                DetectedSection(
                    section_name=h.raw_heading,
                    normalized_section_name=h.canonical,
                    start_page=start_page,
                    end_page=end_page,
                    content=content,
                    confidence_score=round(h.confidence, 3),
                )
            )

        log.info("sections.detected", count=len(sections))
        return sections

    # -- internals -------------------------------------------------------------

    def _match_line(
        self,
        line: str,
        page_number: int,
        offset: int,
        is_transcript: bool,
        report_type: str,
        part: str,
    ) -> _Hit | None:
        # Table-of-contents pointers are not section starts.
        if is_toc_line(line):
            return None

        # 1. SEC item heading (strongest signal for filings).
        item = match_sec_item(line)
        if item is not None:
            code, title = item
            canonical = self.tax.item_canonical(report_type, part, code)
            if canonical:
                return _Hit(
                    page_number, offset, line, canonical, self.tax.confidence_for("sec_item")
                )
            # Unknown item code — try to normalize its trailing title.
            if title:
                res = normalize_heading(title, self.tax)
                if res.canonical:
                    return _Hit(
                        page_number, offset, line, res.canonical,
                        self.tax.confidence_for(res.kind),
                    )
            return None

        # 2. Heading-text match (filings + transcripts).
        if not is_strong_heading(line):
            return None
        res = normalize_heading(line, self.tax)
        if not res.canonical:
            return None

        confidence = self.tax.confidence_for(res.kind)
        # Transcript markers get their (higher) dedicated tier.
        if is_transcript and res.canonical in self._transcript_canonicals:
            confidence = max(confidence, self.tax.confidence_for("transcript_marker"))
        # A fully-uppercase exact heading is a very strong cue.
        if res.kind == "exact_alias" and is_mostly_uppercase(line):
            confidence = max(confidence, self.tax.confidence_for("transcript_marker"))

        return _Hit(page_number, offset, line, res.canonical, confidence)

    def _content_for(self, page_text: dict[int, str], start: int, end: int) -> str:
        parts = [page_text[p] for p in range(start, end + 1) if p in page_text]
        return "\n".join(parts).strip()

    def _fallback_section(
        self, page_text: dict[int, str], first_page: int, last_page: int
    ) -> DetectedSection:
        return DetectedSection(
            section_name=self.tax.fallback_section,
            normalized_section_name=self.tax.fallback_section,
            start_page=first_page,
            end_page=last_page,
            content=self._content_for(page_text, first_page, last_page),
            confidence_score=round(self.tax.fallback_confidence, 3),
        )
