"""Risk evolution data contracts (Phase 4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class RiskMatch:
    """A match between current and previous reporting period's risks."""

    current_id: str | None
    previous_id: str | None
    current_name: str | None
    previous_name: str | None
    category: str
    match_type: str  # EXACT | FUZZY | NONE
    match_score: float


@dataclass
class EvolutionResultRow:
    """Result of classifying a matched/unmatched pair."""

    company_id: str
    current_risk_id: str | None
    previous_risk_id: str | None
    evolution_type: str  # NEW_RISK, REMOVED_RISK, UNCHANGED_RISK, ESCALATED_RISK, REDUCED_RISK
    confidence_score: float
    explanation: str


@dataclass
class EvolutionStats:
    total_current: int = 0
    total_previous: int = 0
    exact_matches: int = 0
    fuzzy_matches: int = 0
    new_risks: int = 0
    removed_risks: int = 0
    escalated_risks: int = 0
    reduced_risks: int = 0
    unchanged_risks: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskEvolutionResult:
    rows: list[EvolutionResultRow]
    stats: EvolutionStats
