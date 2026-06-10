"""Rule-based financial section detection (Phase 1B).

Deterministic, LLM-free detection of logical sections in 10-K / 10-Q filings and
earnings-call transcripts. Public surface:

    from app.ingestion.section_detection import SectionDetector, DetectedSection
"""

from app.ingestion.section_detection.section_detector import (
    DetectedSection,
    SectionDetector,
)

__all__ = ["SectionDetector", "DetectedSection"]
