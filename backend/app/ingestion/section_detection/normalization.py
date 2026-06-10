"""Section-name normalization (Phase 1B).

Maps a raw heading string to a canonical taxonomy name using the configurable
alias map. Returns the canonical name plus the *kind* of match (used to assign a
confidence tier). All vocabulary comes from the Taxonomy — no hardcoded names.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.section_detection.section_patterns import clean_heading
from app.ingestion.section_detection.taxonomy import Taxonomy


@dataclass(frozen=True)
class NormalizationResult:
    canonical: str | None
    kind: str          # 'exact_alias' | 'pattern' | None
    cleaned: str       # cleaned heading text


def normalize_heading(raw: str, taxonomy: Taxonomy) -> NormalizationResult:
    """Resolve a raw heading to a canonical section name, if recognized."""
    cleaned = clean_heading(raw)
    if not cleaned:
        return NormalizationResult(None, "none", cleaned)

    lower = cleaned.lower()

    # 1. Exact alias match (strongest text signal).
    canonical = taxonomy.canonical_for_alias(lower)
    if canonical:
        return NormalizationResult(canonical, "exact_alias", cleaned)

    # 2. Heading equals a canonical name (case-insensitive).
    for canon in taxonomy.canonical_sections:
        if lower == canon.lower():
            return NormalizationResult(canon, "exact_alias", cleaned)

    # 3. Whole-phrase containment: a known alias appears within the heading.
    #    Prefer the longest matching alias to avoid weak partial hits.
    best: str | None = None
    best_alias_len = 0
    for alias, canon in taxonomy.aliases.items():
        if _contains_phrase(lower, alias) and len(alias) > best_alias_len:
            best, best_alias_len = canon, len(alias)
    if best:
        return NormalizationResult(best, "pattern", cleaned)

    return NormalizationResult(None, "none", cleaned)


def _contains_phrase(haystack: str, phrase: str) -> bool:
    """Word-boundary-aware containment so 'business' doesn't match 'businesslike'."""
    idx = haystack.find(phrase)
    if idx == -1:
        return False
    before_ok = idx == 0 or not haystack[idx - 1].isalnum()
    after = idx + len(phrase)
    after_ok = after >= len(haystack) or not haystack[after].isalnum()
    return before_ok and after_ok
