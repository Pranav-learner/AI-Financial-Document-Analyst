"""Confidence scoring for risk extraction (Phase 4).

Maps extraction method + evidence signals to a [0, 1] confidence, mirroring
the Phase 3A metric confidence pattern:

  * HYBRID_VALIDATED (rule + LLM agree): 0.95 base.
  * RULE_BASED: 0.80 base, +0.05 section match.
  * LLM_BASED: 0.70 base, blended with model self-confidence.
  * Disagreement: 0.45 (flagged).

Clamped to [0, 1], 3 dp.
"""

from __future__ import annotations

AGREEMENT = "HYBRID_VALIDATED"
RULE = "RULE_BASED"
LLM = "LLM_BASED"


def compute_risk_confidence(
    method: str,
    *,
    section_match: bool = False,
    llm_confidence: float | None = None,
    disagreement: bool = False,
) -> float:
    if disagreement:
        return 0.45

    if method == AGREEMENT:
        score = 0.95
        if section_match:
            score += 0.03
    elif method == RULE:
        score = 0.80
        if section_match:
            score += 0.05
    elif method == LLM:
        base = 0.70
        if llm_confidence is not None:
            base = 0.60 + 0.15 * max(0.0, min(1.0, llm_confidence))
        score = base + (0.05 if section_match else 0.0)
    else:
        score = 0.50

    return round(max(0.0, min(1.0, score)), 3)
