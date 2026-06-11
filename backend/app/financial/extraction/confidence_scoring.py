"""Confidence scoring (Phase 3A, task §8).

Maps an extraction's method + evidence signals to a [0, 1] confidence. Methodology:

  * **Rule + LLM agree** (HYBRID_VALIDATED): two independent methods produced the
    same value → 0.95, nudged up by section/format evidence (→ up to 0.99).
  * **Rule only** (RULE_BASED): deterministic but single-source → 0.80 base, +0.05
    section match, +0.05 currency/scale present; weak evidence (neither) → 0.60.
  * **LLM only** (LLM_BASED): single, non-deterministic source → 0.70 base, scaled
    by the model's self-reported confidence, +0.05 section match.
  * **Rule vs LLM disagree** → 0.45 (kept but flagged; never silently trusted).

All values are clamped to [0, 1] and rounded to 3 dp (matches the DB column).
"""

from __future__ import annotations

AGREEMENT = "HYBRID_VALIDATED"
RULE = "RULE_BASED"
LLM = "LLM_BASED"


def compute_confidence(
    method: str,
    *,
    section_match: bool = False,
    has_currency_or_scale: bool = True,
    llm_confidence: float | None = None,
    disagreement: bool = False,
) -> float:
    if disagreement:
        return 0.45

    if method == AGREEMENT:
        score = 0.95
        if section_match:
            score += 0.02
        if has_currency_or_scale:
            score += 0.02
    elif method == RULE:
        if not section_match and not has_currency_or_scale:
            score = 0.60  # weak evidence
        else:
            score = 0.80
            if section_match:
                score += 0.05
            if has_currency_or_scale:
                score += 0.05
    elif method == LLM:
        base = 0.70
        if llm_confidence is not None:
            # blend toward the model's self-assessment, but cap its influence
            base = 0.60 + 0.15 * max(0.0, min(1.0, llm_confidence))
        score = base + (0.05 if section_match else 0.0)
    else:  # unknown method → conservative
        score = 0.50

    return round(max(0.0, min(1.0, score)), 3)
