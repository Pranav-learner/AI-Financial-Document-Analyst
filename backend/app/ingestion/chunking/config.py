"""Chunking strategy configuration (Phase 1C).

Defaults come from settings; per-section overrides implement the section-specific
strategies. Keeping this as declarative data (not inline literals in the chunker)
keeps the splitting policy explicit, documented, and tunable.

Section-specific decisions (documented):
  * Risk Factors / Legal Proceedings — lower target so individual risks/items stay
    granular and are not merged together unnecessarily.
  * Financial Statements — larger target + line-first separators to avoid splitting
    tabular data across many tiny chunks; smaller overlap (tables don't need prose overlap).
  * Notes to Financial Statements — slightly larger target (dense, cross-referential).
  * MD&A / Management Commentary / Forward Guidance — prose defaults.
  * Transcript (Prepared Remarks / Q&A / Operator / Closing) — paragraph/turn-based
    defaults; speaker turns are separated by blank lines in our extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.core.config import settings

# Separator hierarchy for recursive splitting (highest-priority first).
_PROSE_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
_TABLE_SEPARATORS = ["\n\n", "\n", " ", ""]


@dataclass(frozen=True)
class StrategyConfig:
    target_tokens: int
    max_tokens: int
    min_tokens: int
    overlap_tokens: int
    separators: list[str] = field(default_factory=lambda: list(_PROSE_SEPARATORS))


def _default() -> StrategyConfig:
    return StrategyConfig(
        target_tokens=settings.chunk_target_tokens,
        max_tokens=settings.chunk_max_tokens,
        min_tokens=settings.chunk_min_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
        separators=list(_PROSE_SEPARATORS),
    )


# Per-canonical-section overrides applied on top of the default.
_OVERRIDES: dict[str, dict] = {
    "Risk Factors": {"target_tokens": 500},
    "Legal Proceedings": {"target_tokens": 500},
    "Financial Statements": {
        "target_tokens": 800,
        "overlap_tokens": 40,
        "separators": list(_TABLE_SEPARATORS),
    },
    "Balance Sheet": {"target_tokens": 800, "overlap_tokens": 40, "separators": list(_TABLE_SEPARATORS)},
    "Income Statement": {"target_tokens": 800, "overlap_tokens": 40, "separators": list(_TABLE_SEPARATORS)},
    "Cash Flow Statement": {"target_tokens": 800, "overlap_tokens": 40, "separators": list(_TABLE_SEPARATORS)},
    "Notes to Financial Statements": {"target_tokens": 800},
}


def get_strategy(normalized_section_name: str | None) -> StrategyConfig:
    """Resolve the chunking strategy for a section (default + overrides)."""
    base = _default()
    overrides = _OVERRIDES.get(normalized_section_name or "", {})
    return replace(base, **overrides) if overrides else base
