"""Hybrid metric extraction (Phase 3A, task §6).

Combines deterministic rule extraction with LLM-assisted extraction and
cross-validates them:

    rule candidates + LLM candidates
        → match by (metric, period)
        → agree?  → HYBRID_VALIDATED (use the deterministic rule value), high conf
        → differ? → keep the RULE value, FLAG the discrepancy, low conf, log it
        → rule only → RULE_BASED ;  LLM only → LLM_BASED
        → deterministic validation → confidence scoring → result

Conflict-resolution strategy: the **rule (deterministic) value always wins** the
stored number; the LLM can raise confidence (agreement) or trigger a flag
(disagreement), but it never overrides a rule value and a disagreement is never
silently stored (ADR-007/ADR-017).
"""

from __future__ import annotations

import time
from decimal import Decimal

from app.core.config import settings
from app.core.logging import get_logger
from app.financial.extraction.confidence_scoring import compute_confidence
from app.financial.extraction.extraction_models import (
    ChunkInput,
    ExtractedMetric,
    ExtractionResult,
    ExtractionStats,
    MetricCandidate,
)
from app.financial.extraction.llm_extractor import LLMExtractor
from app.financial.extraction.rule_extractor import RuleBasedExtractor
from app.financial.extraction.validators import MetricValidator

log = get_logger(__name__)


class HybridExtractor:
    def __init__(
        self,
        *,
        rule_extractor: RuleBasedExtractor | None = None,
        llm_extractor: LLMExtractor | None = None,
        validator: MetricValidator | None = None,
        rel_tol: float | None = None,
    ) -> None:
        self.rule = rule_extractor or RuleBasedExtractor()
        self.llm = llm_extractor or LLMExtractor.from_settings()
        self.validator = validator or MetricValidator()
        self.rel_tol = Decimal(str(rel_tol if rel_tol is not None else settings.metric_agreement_rel_tol))

    def extract(self, chunks: list[ChunkInput]) -> ExtractionResult:
        started = time.monotonic()
        stats = ExtractionStats(chunks_processed=len(chunks))

        rule_candidates = self.rule.extract(chunks)
        llm_candidates = self.llm.extract(chunks)
        if self.llm.enabled is False:
            stats.llm_errors = 0
        stats.rule_hits = len(rule_candidates)
        stats.llm_hits = len(llm_candidates)

        rule_by = self._best_by_key(rule_candidates)
        llm_by = self._best_by_key(llm_candidates)

        metrics: list[ExtractedMetric] = []
        for key in set(rule_by) | set(llm_by):
            metric = self._resolve(rule_by.get(key), llm_by.get(key), stats)
            if metric is not None:
                metrics.append(metric)

        stats.metrics_extracted = len(metrics)
        stats.duration_seconds = round(time.monotonic() - started, 3)
        log.info("extraction.run_complete", **stats.as_dict())
        return ExtractionResult(metrics=metrics, stats=stats)

    # ---- resolution ----------------------------------------------------------

    def _resolve(
        self, r: MetricCandidate | None, ll: MetricCandidate | None, stats: ExtractionStats
    ) -> ExtractedMetric | None:
        if r is not None and ll is not None:
            if self._agree(r.value, ll.value):
                stats.agreements += 1
                conf = compute_confidence(
                    "HYBRID_VALIDATED",
                    section_match=r.section_match or ll.section_match,
                    has_currency_or_scale=r.has_currency_or_scale,
                )
                meta = {"rule_value": str(r.value), "llm_value": str(ll.value), "agreement": True}
                return self._finalize(r, "HYBRID_VALIDATED", conf, meta, stats)

            stats.disagreements += 1
            log.warning(
                "extraction.discrepancy",
                metric=r.normalized_metric_name,
                rule_value=str(r.value),
                llm_value=str(ll.value),
            )
            conf = compute_confidence(
                "RULE_BASED",
                section_match=r.section_match,
                has_currency_or_scale=r.has_currency_or_scale,
                disagreement=True,
            )
            meta = {"rule_value": str(r.value), "llm_value": str(ll.value), "discrepancy": True}
            return self._finalize(r, "RULE_BASED", conf, meta, stats)

        if r is not None:
            conf = compute_confidence(
                "RULE_BASED",
                section_match=r.section_match,
                has_currency_or_scale=r.has_currency_or_scale,
            )
            return self._finalize(r, "RULE_BASED", conf, {}, stats)

        # LLM only
        assert ll is not None
        conf = compute_confidence(
            "LLM_BASED",
            section_match=ll.section_match,
            has_currency_or_scale=ll.has_currency_or_scale,
            llm_confidence=ll.raw_confidence,
        )
        return self._finalize(ll, "LLM_BASED", conf, {}, stats)

    def _finalize(
        self,
        cand: MetricCandidate,
        method: str,
        confidence: float,
        meta: dict,
        stats: ExtractionStats,
    ) -> ExtractedMetric | None:
        vr = self.validator.validate(cand)
        if not vr.is_valid:
            stats.validation_failures += 1
            return None
        metadata = dict(meta)
        if vr.warnings:
            metadata["warnings"] = vr.warnings
        return ExtractedMetric(
            normalized_metric_name=cand.normalized_metric_name,
            metric_name=cand.metric_name,
            category=cand.category,
            value=cand.value,
            currency=cand.currency,
            unit=cand.unit,
            fiscal_year=cand.fiscal_year,
            fiscal_quarter=cand.fiscal_quarter,
            source_chunk_id=cand.source_chunk_id,
            source_text=cand.source_text,
            extraction_method=method,
            confidence_score=confidence,
            extraction_metadata=metadata,
        )

    def _agree(self, a: Decimal, b: Decimal) -> bool:
        if a == b:
            return True
        magnitude = max(abs(a), abs(b))
        if magnitude == 0:
            return True
        return abs(a - b) <= self.rel_tol * magnitude

    @staticmethod
    def _best_by_key(candidates: list[MetricCandidate]) -> dict[tuple, MetricCandidate]:
        best: dict[tuple, MetricCandidate] = {}
        for c in candidates:
            cur = best.get(c.key())
            if cur is None or c.raw_confidence > cur.raw_confidence:
                best[c.key()] = c
        return best
