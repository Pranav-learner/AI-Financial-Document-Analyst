"""RiskEvolutionService (Phase 4).

Orchestrates matching, classification, and validation of risk evolution
across reporting periods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.risk.evolution.evolution_classifier import RiskEvolutionClassifier
from app.risk.evolution.models import EvolutionResultRow, EvolutionStats, RiskEvolutionResult
from app.risk.evolution.risk_matcher import RiskMatcher
from app.risk.evolution.validators import EvolutionValidator

if TYPE_CHECKING:
    from app.models.risk_factor import RiskFactor

log = get_logger(__name__)


class RiskEvolutionService:
    def __init__(
        self,
        *,
        matcher: RiskMatcher | None = None,
        classifier: RiskEvolutionClassifier | None = None,
        validator: EvolutionValidator | None = None,
    ) -> None:
        self.matcher = matcher or RiskMatcher()
        self.classifier = classifier or RiskEvolutionClassifier()
        self.validator = validator or EvolutionValidator()

    def build_evolution(
        self,
        company_id: str,
        current_risks: list[RiskFactor],
        previous_risks: list[RiskFactor],
    ) -> RiskEvolutionResult:
        """Calculate evolution of risks from previous to current reporting period."""
        stats = EvolutionStats(
            total_current=len(current_risks),
            total_previous=len(previous_risks),
        )

        matches = self.matcher.match_risks(current_risks, previous_risks)

        current_map = {str(r.id): r for r in current_risks}
        previous_map = {str(r.id): r for r in previous_risks}

        rows: list[EvolutionResultRow] = []

        for m in matches:
            # Stats counting
            if m.match_type == "EXACT":
                stats.exact_matches += 1
            elif m.match_type == "FUZZY":
                stats.fuzzy_matches += 1

            row = self.classifier.classify(m, company_id, current_map, previous_map)

            # Validate before adding
            vr = self.validator.validate(row)
            if not vr.is_valid:
                continue

            # Update action-based stats
            if row.evolution_type == "NEW_RISK":
                stats.new_risks += 1
            elif row.evolution_type == "REMOVED_RISK":
                stats.removed_risks += 1
            elif row.evolution_type == "UNCHANGED_RISK":
                stats.unchanged_risks += 1
            elif row.evolution_type == "ESCALATED_RISK":
                stats.escalated_risks += 1
            elif row.evolution_type == "REDUCED_RISK":
                stats.reduced_risks += 1

            rows.append(row)

        log.info(
            "risk_evolution.completed",
            company_id=company_id,
            rows=len(rows),
            **stats.as_dict(),
        )
        return RiskEvolutionResult(rows=rows, stats=stats)
