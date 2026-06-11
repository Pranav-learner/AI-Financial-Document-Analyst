"""Financial metric extraction engine (Phase 3A).

Hybrid extraction: deterministic rule-based + LLM-assisted, cross-validated, with
deterministic validation, confidence scoring, normalization, and full source
traceability. The LLM assists; it is never the source of truth (ADR-007/ADR-017).

    from app.financial.extraction import (
        HybridExtractor, RuleBasedExtractor, LLMExtractor,
        MetricValidator, ChunkInput, ExtractionResult,
    )
"""

from app.financial.extraction.confidence_scoring import compute_confidence
from app.financial.extraction.exceptions import (
    ExtractionError,
    LLMExtractionError,
    LLMResponseError,
    LLMTransientError,
)
from app.financial.extraction.extraction_models import (
    ChunkInput,
    ExtractedMetric,
    ExtractionResult,
    ExtractionStats,
    MetricCandidate,
)
from app.financial.extraction.hybrid_extractor import HybridExtractor
from app.financial.extraction.llm_extractor import LLMExtractor
from app.financial.extraction.rule_extractor import RuleBasedExtractor
from app.financial.extraction.validators import MetricValidator, ValidationResult

__all__ = [
    "HybridExtractor",
    "RuleBasedExtractor",
    "LLMExtractor",
    "MetricValidator",
    "ValidationResult",
    "ChunkInput",
    "MetricCandidate",
    "ExtractedMetric",
    "ExtractionResult",
    "ExtractionStats",
    "compute_confidence",
    "ExtractionError",
    "LLMExtractionError",
    "LLMResponseError",
    "LLMTransientError",
]
