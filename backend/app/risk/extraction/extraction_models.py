"""Risk extraction data contracts (Phase 4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class RiskChunkInput:
    """A candidate chunk fed to the risk extractors."""

    chunk_id: str | None
    text: str
    normalized_section_name: str | None
    fiscal_year: int | None
    fiscal_quarter: int | None


@dataclass
class RiskCandidate:
    """A raw risk extraction (pre-validation), from rule OR LLM."""

    risk_name: str
    normalized_risk_name: str
    risk_description: str
    category: str
    severity: str
    source_chunk_id: str | None
    source_text: str
    method: str  # RULE_BASED | LLM_BASED
    raw_confidence: float
    section_match: bool = False
    extraction_metadata: dict = field(default_factory=dict)

    def key(self) -> str:
        """Deduplication key: normalized name."""
        return self.normalized_risk_name


@dataclass
class ExtractedRisk:
    """A validated, normalized, scored risk — ready to persist."""

    risk_name: str
    normalized_risk_name: str
    risk_description: str
    category: str
    severity: str
    source_chunk_id: str | None
    source_text: str
    extraction_method: str
    confidence_score: float
    extraction_metadata: dict = field(default_factory=dict)


@dataclass
class RiskExtractionStats:
    """Observability for an extraction run."""

    chunks_processed: int = 0
    rule_hits: int = 0
    llm_hits: int = 0
    agreements: int = 0
    disagreements: int = 0
    validation_failures: int = 0
    risks_extracted: int = 0
    llm_errors: int = 0
    duration_seconds: float = 0.0

    @property
    def agreement_rate(self) -> float:
        total = self.agreements + self.disagreements
        return round(self.agreements / total, 4) if total else 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["agreement_rate"] = self.agreement_rate
        return d


@dataclass
class RiskExtractionResult:
    risks: list[ExtractedRisk]
    stats: RiskExtractionStats
