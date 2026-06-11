"""Extraction data contracts (Phase 3A)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal


@dataclass
class ChunkInput:
    """A candidate chunk fed to the extractors."""

    chunk_id: str | None
    text: str
    normalized_section_name: str | None
    fiscal_year: int | None
    fiscal_quarter: int | None


@dataclass
class MetricCandidate:
    """A raw extraction (pre-validation), from rule OR LLM."""

    normalized_metric_name: str
    metric_name: str                 # surface form found / returned
    category: str
    value: Decimal
    currency: str | None
    unit: str
    fiscal_year: int | None
    fiscal_quarter: int | None
    source_chunk_id: str | None
    source_text: str
    method: str                      # RULE_BASED | LLM_BASED
    raw_confidence: float
    has_currency_or_scale: bool = False
    section_match: bool = False

    def key(self) -> tuple[str, int | None, int | None]:
        return (self.normalized_metric_name, self.fiscal_year, self.fiscal_quarter)


@dataclass
class ExtractedMetric:
    """A validated, normalized, scored metric — ready to persist."""

    normalized_metric_name: str
    metric_name: str
    category: str
    value: Decimal
    currency: str | None
    unit: str
    fiscal_year: int | None
    fiscal_quarter: int | None
    source_chunk_id: str | None
    source_text: str
    extraction_method: str
    confidence_score: float
    extraction_metadata: dict = field(default_factory=dict)


@dataclass
class ExtractionStats:
    """Observability for an extraction run (task §15)."""

    chunks_processed: int = 0
    rule_hits: int = 0
    llm_hits: int = 0
    agreements: int = 0
    disagreements: int = 0
    validation_failures: int = 0
    metrics_extracted: int = 0
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
class ExtractionResult:
    metrics: list[ExtractedMetric]
    stats: ExtractionStats
