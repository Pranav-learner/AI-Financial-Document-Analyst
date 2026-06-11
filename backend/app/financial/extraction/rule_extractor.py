"""Rule-based metric extraction (Phase 3A, task §4).

Deterministic, high-precision extraction: locate a metric alias (from the
taxonomy) in a financial-section chunk, then bind the nearest matching value
(currency vs percent according to the metric's kind). Section-aware (a metric
found in its expected section is more trustworthy). No LLM.

This is the deterministic backbone — its values are the source of truth that the
LLM is later cross-checked against (ADR-007/ADR-017).
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.financial.extraction.extraction_models import ChunkInput, MetricCandidate
from app.financial.metrics.metric_aliases import find_aliases_in_text
from app.financial.metrics.normalization import NormalizedValue, find_values
from app.financial.metrics.taxonomy import MetricTaxonomy, get_metric_taxonomy

log = get_logger(__name__)

_YEAR_LIKE = re.compile(r"^\d{4}$")


def _is_year_like(v: NormalizedValue) -> bool:
    return (
        v.unit == "ABSOLUTE"
        and v.currency is None
        and not v.is_percent
        and bool(_YEAR_LIKE.match(v.raw.strip("()")))
        and 1900 <= int(v.value if v.value >= 0 else -v.value) <= 2100
    )


class RuleBasedExtractor:
    def __init__(self, *, taxonomy: MetricTaxonomy | None = None, window: int = 90) -> None:
        self.tax = taxonomy or get_metric_taxonomy()
        self.window = window

    def extract(self, chunks: list[ChunkInput]) -> list[MetricCandidate]:
        out: list[MetricCandidate] = []
        for ch in chunks:
            out.extend(self._extract_chunk(ch))
        return out

    def _extract_chunk(self, ch: ChunkInput) -> list[MetricCandidate]:
        candidates: list[MetricCandidate] = []
        for canonical, surface, s, e in find_aliases_in_text(ch.text, taxonomy=self.tax):
            definition = self.tax.get(canonical)
            if definition is None:
                continue
            value = self._best_value(ch.text, e, definition.value_kind)
            if value is None:
                continue
            section_match = ch.normalized_section_name in definition.expected_sections
            snippet_end = min(len(ch.text), e + value.end + 5)
            snippet = ch.text[max(0, s - 25) : snippet_end].strip()
            candidates.append(
                MetricCandidate(
                    normalized_metric_name=canonical,
                    metric_name=surface,
                    category=definition.category,
                    value=value.value,
                    currency=value.currency,
                    unit=value.unit,
                    fiscal_year=ch.fiscal_year,
                    fiscal_quarter=ch.fiscal_quarter,
                    source_chunk_id=ch.chunk_id,
                    source_text=snippet,
                    method="RULE_BASED",
                    raw_confidence=self._raw_confidence(value, section_match),
                    has_currency_or_scale=value.has_currency_or_scale,
                    section_match=section_match,
                )
            )
        return self._dedupe(candidates)

    def _best_value(self, text: str, after: int, value_kind: str) -> NormalizedValue | None:
        window_text = text[after : after + self.window]
        matching = [
            v for v in find_values(window_text)
            if (v.is_percent if value_kind == "percent" else not v.is_percent)
        ]
        if not matching:
            return None
        # Prefer a value that carries currency/scale; then a non-year-like number.
        for predicate in (
            lambda v: v.has_currency_or_scale,
            lambda v: not _is_year_like(v),
            lambda v: True,
        ):
            for v in matching:
                if predicate(v):
                    return v
        return None

    @staticmethod
    def _raw_confidence(value: NormalizedValue, section_match: bool) -> float:
        conf = 0.70
        if value.has_currency_or_scale:
            conf += 0.10
        if section_match:
            conf += 0.05
        return min(conf, 0.85)

    @staticmethod
    def _dedupe(candidates: list[MetricCandidate]) -> list[MetricCandidate]:
        """Per (metric, period) keep the highest-confidence candidate in a chunk."""
        best: dict[tuple, MetricCandidate] = {}
        for c in candidates:
            cur = best.get(c.key())
            if cur is None or c.raw_confidence > cur.raw_confidence:
                best[c.key()] = c
        return list(best.values())
