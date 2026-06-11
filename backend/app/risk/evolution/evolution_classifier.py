"""RiskEvolutionClassifier (Phase 4).

Classifies matched/unmatched risk pairs into evolution categories based on severity
deltas:
  * NEW_RISK: risk appears in current period, not previous.
  * REMOVED_RISK: risk was in previous period, not current.
  * UNCHANGED_RISK: risk exists in both, severity matches.
  * ESCALATED_RISK: risk exists in both, severity increased.
  * REDUCED_RISK: risk exists in both, severity decreased.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.risk.evolution.models import EvolutionResultRow, RiskMatch

if TYPE_CHECKING:
    from app.models.risk_factor import RiskFactor

_SEVERITY_WEIGHTS = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


class RiskEvolutionClassifier:
    def classify(
        self,
        match: RiskMatch,
        company_id: str,
        current_map: dict[str, RiskFactor],
        previous_map: dict[str, RiskFactor],
    ) -> EvolutionResultRow:
        """Classify a matched pair of risks into an evolution category."""
        # Case 1: New Risk
        if match.previous_id is None:
            curr = current_map[match.current_id]
            explanation = (
                f"New {curr.category.replace('_', ' ').title()} risk disclosed "
                f"('{curr.risk_name}') with {curr.severity} severity."
            )
            return EvolutionResultRow(
                company_id=company_id,
                current_risk_id=match.current_id,
                previous_risk_id=None,
                evolution_type="NEW_RISK",
                confidence_score=float(curr.confidence_score),
                explanation=explanation,
            )

        # Case 2: Removed Risk
        if match.current_id is None:
            prev = previous_map[match.previous_id]
            explanation = (
                f"Risk related to {prev.category.replace('_', ' ').title()} "
                f"('{prev.risk_name}') has been removed from disclosures."
            )
            return EvolutionResultRow(
                company_id=company_id,
                current_risk_id=None,
                previous_risk_id=match.previous_id,
                evolution_type="REMOVED_RISK",
                # Retain confidence of the prior extraction as the confidence of the action
                confidence_score=float(prev.confidence_score),
                explanation=explanation,
            )

        # Case 3: Matched Risk (Compare severities)
        curr = current_map[match.current_id]
        prev = previous_map[match.previous_id]

        curr_weight = _SEVERITY_WEIGHTS.get(curr.severity, 2)
        prev_weight = _SEVERITY_WEIGHTS.get(prev.severity, 2)

        # Blend confidences
        confidence = round((float(curr.confidence_score) + float(prev.confidence_score)) / 2.0, 3)

        if curr_weight > prev_weight:
            evolution_type = "ESCALATED_RISK"
            explanation = (
                f"Risk '{curr.risk_name}' escalated from {prev.severity} "
                f"to {curr.severity} severity."
            )
        elif curr_weight < prev_weight:
            evolution_type = "REDUCED_RISK"
            explanation = (
                f"Risk '{curr.risk_name}' reduced from {prev.severity} "
                f"to {curr.severity} severity."
            )
        else:
            evolution_type = "UNCHANGED_RISK"
            explanation = (
                f"Risk '{curr.risk_name}' remained unchanged at "
                f"{curr.severity} severity."
            )

        return EvolutionResultRow(
            company_id=company_id,
            current_risk_id=match.current_id,
            previous_risk_id=match.previous_id,
            evolution_type=evolution_type,
            confidence_score=confidence,
            explanation=explanation,
        )
