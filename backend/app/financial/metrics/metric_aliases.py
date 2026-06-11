"""Metric alias resolution (Phase 3A).

Maps surface forms found in text ("Net Sales", "Total Revenue") to a canonical
metric name ("REVENUE"). All alias knowledge comes from the taxonomy — nothing is
hardcoded here. Longest-alias-first matching avoids a short alias ("sales")
shadowing a more specific one ("total net sales").
"""

from __future__ import annotations

import re

from app.financial.metrics.taxonomy import MetricTaxonomy, get_metric_taxonomy


def _normalize_surface(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def resolve_alias(text: str, *, taxonomy: MetricTaxonomy | None = None) -> str | None:
    """Exact (normalized) alias → canonical, or None."""
    tax = taxonomy or get_metric_taxonomy()
    return tax.alias_to_canonical.get(_normalize_surface(text))


def find_aliases_in_text(
    text: str, *, taxonomy: MetricTaxonomy | None = None
) -> list[tuple[str, str, int, int]]:
    """Locate metric aliases in free text.

    Returns (canonical, matched_surface, start, end) for each occurrence, ordered
    by position. Longer aliases win over overlapping shorter ones at the same span.
    """
    tax = taxonomy or get_metric_taxonomy()
    lowered = text.lower()
    # Sort aliases longest-first so specific phrases match before generic ones.
    aliases = sorted(tax.alias_to_canonical.keys(), key=len, reverse=True)

    spans: list[tuple[str, str, int, int]] = []
    claimed: list[tuple[int, int]] = []
    for alias in aliases:
        pattern = r"\b" + re.escape(alias) + r"\b"
        for m in re.finditer(pattern, lowered):
            s, e = m.start(), m.end()
            if any(s < ce and cs < e for cs, ce in claimed):  # overlaps a longer match
                continue
            claimed.append((s, e))
            spans.append((tax.alias_to_canonical[alias], text[s:e], s, e))
    spans.sort(key=lambda x: x[2])
    return spans
