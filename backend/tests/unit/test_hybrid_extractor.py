"""Unit tests for the hybrid extractor: cross-validation + conflict resolution (Phase 3A)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.financial.extraction.extraction_models import ChunkInput, MetricCandidate
from app.financial.extraction.hybrid_extractor import HybridExtractor
from app.financial.extraction.rule_extractor import RuleBasedExtractor


def _chunk(text="Total revenue was $96.7 billion in fiscal 2024."):
    return ChunkInput(chunk_id="c1", text=text, normalized_section_name="Income Statement",
                      fiscal_year=2024, fiscal_quarter=None)


def _llm_candidate(value, *, name="REVENUE", year=2024, currency="USD", unit="BILLION"):
    return MetricCandidate(
        normalized_metric_name=name, metric_name="Revenue", category="REVENUE",
        value=Decimal(str(value)), currency=currency, unit=unit, fiscal_year=year,
        fiscal_quarter=None, source_chunk_id="c1", source_text="...", method="LLM_BASED",
        raw_confidence=0.8, has_currency_or_scale=True, section_match=True,
    )


class FakeLLM:
    def __init__(self, candidates) -> None:
        self.enabled = True
        self._c = candidates

    def extract(self, chunks):
        return self._c


@pytest.mark.unit
def test_agreement_yields_hybrid_validated() -> None:
    he = HybridExtractor(llm_extractor=FakeLLM([_llm_candidate("96700000000")]))
    res = he.extract([_chunk()])
    rev = next(m for m in res.metrics if m.normalized_metric_name == "REVENUE")
    assert rev.extraction_method == "HYBRID_VALIDATED"
    assert rev.confidence_score >= 0.95
    assert rev.value == Decimal("96700000000")           # deterministic rule value
    assert res.stats.agreements == 1


@pytest.mark.unit
def test_disagreement_keeps_rule_value_and_flags() -> None:
    he = HybridExtractor(llm_extractor=FakeLLM([_llm_candidate("89200000000")]))
    res = he.extract([_chunk()])
    rev = next(m for m in res.metrics if m.normalized_metric_name == "REVENUE")
    assert rev.extraction_method == "RULE_BASED"          # NOT silently stored as LLM value
    assert rev.value == Decimal("96700000000.0")          # rule wins
    assert rev.confidence_score == 0.45
    assert rev.extraction_metadata.get("discrepancy") is True
    assert rev.extraction_metadata["llm_value"] == "89200000000"
    assert res.stats.disagreements == 1


@pytest.mark.unit
def test_rule_only_when_llm_disabled() -> None:
    from app.financial.extraction.llm_extractor import LLMExtractor

    he = HybridExtractor(llm_extractor=LLMExtractor(api_key="", model="x"))
    res = he.extract([_chunk()])
    rev = next(m for m in res.metrics if m.normalized_metric_name == "REVENUE")
    assert rev.extraction_method == "RULE_BASED"
    assert res.stats.llm_hits == 0


@pytest.mark.unit
def test_llm_only_when_rule_finds_nothing() -> None:
    # No parseable number → rule yields nothing; LLM supplies the metric.
    he = HybridExtractor(llm_extractor=FakeLLM([_llm_candidate("96700000000")]))
    res = he.extract([_chunk(text="Revenue performance was strong this year.")])
    rev = next(m for m in res.metrics if m.normalized_metric_name == "REVENUE")
    assert rev.extraction_method == "LLM_BASED"


@pytest.mark.unit
def test_invalid_candidate_dropped_by_validation() -> None:
    bad = MetricCandidate(
        normalized_metric_name="REVENUE", metric_name="Revenue", category="REVENUE",
        value=Decimal("100"), currency="ZZZ", unit="BILLION", fiscal_year=2024,
        fiscal_quarter=None, source_chunk_id="c1", source_text="x", method="RULE_BASED",
        raw_confidence=0.8,
    )

    class FakeRule(RuleBasedExtractor):
        def extract(self, chunks):
            return [bad]

    from app.financial.extraction.llm_extractor import LLMExtractor

    he = HybridExtractor(rule_extractor=FakeRule(), llm_extractor=LLMExtractor(api_key="", model="x"))
    res = he.extract([_chunk()])
    assert res.metrics == []
    assert res.stats.validation_failures == 1
