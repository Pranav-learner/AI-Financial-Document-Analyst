"""Deterministic evolution validation (Phase 4).

Every classified risk evolution must pass these checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.risk.evolution.models import EvolutionResultRow

log = get_logger(__name__)

_VALID_EVOLUTION_TYPES = {
    "NEW_RISK", "REMOVED_RISK", "UNCHANGED_RISK", "ESCALATED_RISK", "REDUCED_RISK",
}


@dataclass
class EvolutionValidationResult:
    fatal: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal


class EvolutionValidator:
    def validate(self, row: EvolutionResultRow) -> EvolutionValidationResult:
        result = EvolutionValidationResult()

        if not row.company_id:
            result.fatal.append("missing_company_id")

        if row.evolution_type not in _VALID_EVOLUTION_TYPES:
            result.fatal.append(f"invalid_evolution_type:{row.evolution_type}")

        if row.current_risk_id is None and row.previous_risk_id is None:
            result.fatal.append("missing_both_risk_ids")

        if row.evolution_type == "NEW_RISK" and row.current_risk_id is None:
            result.fatal.append("new_risk_missing_current_id")

        if row.evolution_type == "REMOVED_RISK" and row.previous_risk_id is None:
            result.fatal.append("removed_risk_missing_previous_id")

        if not row.explanation.strip():
            result.fatal.append("missing_explanation")

        if not result.is_valid:
            log.warning(
                "risk_evolution.validation_failed",
                evolution_type=row.evolution_type,
                company_id=row.company_id,
                issues=result.fatal,
            )
        return result
