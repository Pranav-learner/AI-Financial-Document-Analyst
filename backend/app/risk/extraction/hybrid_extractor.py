"""Hybrid risk extraction (Phase 4).

Combines deterministic rule-based risk detection with LLM-assisted risk extraction,
and cross-validates them:
  * rule candidates + LLM candidates
      → match by normalized_risk_name
      → agree?  → HYBRID_VALIDATED (use rule/agreed values), high confidence
      → differ? → keep the RULE value/category/severity, flag discrepancy, low confidence
      → rule only → RULE_BASED
      → LLM only → LLM_BASED
"""

from __future__ import annotations

import time

from app.core.logging import get_logger
from app.risk.extraction.confidence_scoring import compute_risk_confidence
from app.risk.extraction.extraction_models import (
    ExtractedRisk,
    RiskCandidate,
    RiskChunkInput,
    RiskExtractionResult,
    RiskExtractionStats,
)
from app.risk.extraction.llm_extractor import RiskLLMExtractor
from app.risk.extraction.rule_extractor import RuleBasedRiskExtractor
from app.risk.extraction.validators import RiskValidator

log = get_logger(__name__)


class HybridRiskExtractor:
    def __init__(
        self,
        *,
        rule_extractor: RuleBasedRiskExtractor | None = None,
        llm_extractor: RiskLLMExtractor | None = None,
        validator: RiskValidator | None = None,
    ) -> None:
        self.rule = rule_extractor or RuleBasedRiskExtractor()
        self.llm = llm_extractor or RiskLLMExtractor.from_settings()
        self.validator = validator or RiskValidator()

    def extract(self, chunks: list[RiskChunkInput]) -> RiskExtractionResult:
        started = time.monotonic()
        stats = RiskExtractionStats(chunks_processed=len(chunks))

        rule_candidates = self.rule.extract(chunks)
        llm_candidates = self.llm.extract(chunks)
        
        if self.llm.enabled is False:
            stats.llm_errors = 0
            
        stats.rule_hits = len(rule_candidates)
        stats.llm_hits = len(llm_candidates)

        rule_by = self._best_by_key(rule_candidates)
        llm_by = self._best_by_key(llm_candidates)

        risks: list[ExtractedRisk] = []
        for key in set(rule_by) | set(llm_by):
            risk = self._resolve(rule_by.get(key), llm_by.get(key), stats)
            if risk is not None:
                risks.append(risk)

        stats.risks_extracted = len(risks)
        stats.duration_seconds = round(time.monotonic() - started, 3)
        log.info("risk_extraction.run_complete", **stats.as_dict())
        return RiskExtractionResult(risks=risks, stats=stats)

    def _resolve(
        self,
        r: RiskCandidate | None,
        ll: RiskCandidate | None,
        stats: RiskExtractionStats,
    ) -> ExtractedRisk | None:
        if r is not None and ll is not None:
            # Match exists. Check category & severity agreement.
            category_agree = r.category == ll.category
            severity_agree = r.severity == ll.severity

            if category_agree and severity_agree:
                stats.agreements += 1
                conf = compute_risk_confidence(
                    "HYBRID_VALIDATED",
                    section_match=r.section_match or ll.section_match,
                )
                meta = {
                    "rule_category": r.category,
                    "llm_category": ll.category,
                    "rule_severity": r.severity,
                    "llm_severity": ll.severity,
                    "agreement": True,
                }
                return self._finalize(r, "HYBRID_VALIDATED", conf, meta, stats)

            stats.disagreements += 1
            log.warning(
                "risk_extraction.discrepancy",
                risk=r.normalized_risk_name,
                rule_category=r.category,
                llm_category=ll.category,
                rule_severity=r.severity,
                llm_severity=ll.severity,
            )
            conf = compute_risk_confidence(
                "RULE_BASED",
                section_match=r.section_match,
                disagreement=True,
            )
            meta = {
                "rule_category": r.category,
                "llm_category": ll.category,
                "rule_severity": r.severity,
                "llm_severity": ll.severity,
                "discrepancy": True,
            }
            # Keep rule as the fallback anchor
            return self._finalize(r, "RULE_BASED", conf, meta, stats)

        if r is not None:
            conf = compute_risk_confidence(
                "RULE_BASED",
                section_match=r.section_match,
            )
            return self._finalize(r, "RULE_BASED", conf, {}, stats)

        # LLM only
        assert ll is not None
        conf = compute_risk_confidence(
            "LLM_BASED",
            section_match=ll.section_match,
            llm_confidence=ll.raw_confidence,
        )
        return self._finalize(ll, "LLM_BASED", conf, {}, stats)

    def _finalize(
        self,
        cand: RiskCandidate,
        method: str,
        confidence: float,
        meta: dict,
        stats: RiskExtractionStats,
    ) -> ExtractedRisk | None:
        vr = self.validator.validate(cand)
        if not vr.is_valid:
            stats.validation_failures += 1
            return None
        metadata = dict(meta)
        if vr.warnings:
            metadata["warnings"] = vr.warnings
        return ExtractedRisk(
            risk_name=cand.risk_name,
            normalized_risk_name=cand.normalized_risk_name,
            risk_description=cand.risk_description,
            category=cand.category,
            severity=cand.severity,
            source_chunk_id=cand.source_chunk_id,
            source_text=cand.source_text,
            extraction_method=method,
            confidence_score=confidence,
            extraction_metadata=metadata,
        )

    @staticmethod
    def _best_by_key(candidates: list[RiskCandidate]) -> dict[str, RiskCandidate]:
        best: dict[str, RiskCandidate] = {}
        for c in candidates:
            cur = best.get(c.key())
            if cur is None or c.raw_confidence > cur.raw_confidence:
                best[c.key()] = c
        return best
