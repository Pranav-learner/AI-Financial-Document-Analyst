"""Unit tests for Phase 4 Risk Extraction Engine."""

from __future__ import annotations

import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.risk.extraction.extraction_models import RiskChunkInput, RiskCandidate, ExtractedRisk
from app.risk.extraction.rule_extractor import RuleBasedRiskExtractor
from app.risk.extraction.severity_classifier import SeverityClassifier
from app.risk.extraction.validators import RiskValidator
from app.risk.extraction.hybrid_extractor import HybridRiskExtractor
from app.risk.extraction.confidence_scoring import compute_risk_confidence
from app.risk.taxonomy.normalization import normalize_risk_name, normalize_category


def test_severity_classifier():
    classifier = SeverityClassifier()
    assert classifier.classify("We anticipate a minor and limited delay.") == "LOW"
    assert classifier.classify("This may impact our quarterly revenue moderately.") == "MEDIUM"
    assert classifier.classify("We face significant and material adverse impacts.") == "HIGH"
    assert classifier.classify("This poses an existential threat and severe impairment.") == "CRITICAL"
    assert classifier.classify("Normal business operations continue.") == "MEDIUM"  # Default fallback


def test_risk_validator():
    validator = RiskValidator()

    # Valid candidate
    valid_cand = RiskCandidate(
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        risk_description="We face issues with supply chain shipping.",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        source_chunk_id="chunk-123",
        source_text="We face issues with supply chain shipping.",
        method="RULE_BASED",
        raw_confidence=0.8,
        section_match=True
    )
    result = validator.validate(valid_cand)
    assert result.is_valid is True

    # Invalid empty name
    invalid_cand = RiskCandidate(
        risk_name="",
        normalized_risk_name="",
        risk_description="Description",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        source_chunk_id="chunk-123",
        source_text="Source",
        method="RULE_BASED",
        raw_confidence=0.8
    )
    result = validator.validate(invalid_cand)
    assert result.is_valid is False

    # Invalid category
    invalid_cat = RiskCandidate(
        risk_name="Fake Risk",
        normalized_risk_name="fake_risk",
        risk_description="Description",
        category="INVALID_CATEGORY",
        severity="HIGH",
        source_chunk_id="chunk-123",
        source_text="Source",
        method="RULE_BASED",
        raw_confidence=0.8
    )
    result = validator.validate(invalid_cat)
    assert result.is_valid is False


def test_rule_based_extractor():
    extractor = RuleBasedRiskExtractor()

    # Test chunk with no trigger
    chunk_no_trigger = RiskChunkInput(
        chunk_id="chunk-1",
        text="Normal operating procedure is active.",
        normalized_section_name="Business Description",
        fiscal_year=2026,
        fiscal_quarter=1
    )
    assert len(extractor.extract([chunk_no_trigger])) == 0

    # Test chunk with trigger and taxonomy keyword
    chunk_with_risk = RiskChunkInput(
        chunk_id="chunk-2",
        text="We face significant disruption to our supply chain which poses a major risk.",
        normalized_section_name="Risk Factors",
        fiscal_year=2026,
        fiscal_quarter=1
    )
    candidates = extractor.extract([chunk_with_risk])
    assert len(candidates) > 0
    candidate = candidates[0]
    assert "Supply Chain" in candidate.risk_name
    assert candidate.category == "SUPPLY_CHAIN"
    assert candidate.severity == "HIGH"  # matches "significant disruption"
    assert candidate.section_match is True


def test_hybrid_risk_extractor_agreement():
    # Stub rule and LLM extractors
    rule_mock = MagicMock()
    llm_mock = MagicMock()

    rule_cand = RiskCandidate(
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        risk_description="Supply chain delay.",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        source_chunk_id="chunk-1",
        source_text="Supply chain delay.",
        method="RULE_BASED",
        raw_confidence=0.8,
        section_match=True
    )
    rule_mock.extract.return_value = [rule_cand]

    llm_cand = RiskCandidate(
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        risk_description="Supply chain delay.",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        source_chunk_id="chunk-1",
        source_text="Supply chain delay.",
        method="LLM_BASED",
        raw_confidence=0.9,
        section_match=True
    )
    llm_mock.extract.return_value = [llm_cand]

    extractor = HybridRiskExtractor(
        rule_extractor=rule_mock,
        llm_extractor=llm_mock
    )

    result = extractor.extract([RiskChunkInput(
        chunk_id="chunk-1",
        text="Supply chain delay.",
        normalized_section_name="Risk Factors",
        fiscal_year=2026,
        fiscal_quarter=1
    )])

    assert len(result.risks) == 1
    risk = result.risks[0]
    assert risk.extraction_method == "HYBRID_VALIDATED"
    assert risk.category == "SUPPLY_CHAIN"
    assert risk.severity == "HIGH"
    assert risk.confidence_score == 0.98  # HYBRID_VALIDATED with section match
    assert result.stats.agreements == 1


def test_hybrid_risk_extractor_disagreement():
    rule_mock = MagicMock()
    llm_mock = MagicMock()

    rule_cand = RiskCandidate(
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        risk_description="Supply chain delay.",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        source_chunk_id="chunk-1",
        source_text="Supply chain delay.",
        method="RULE_BASED",
        raw_confidence=0.8,
        section_match=True
    )
    rule_mock.extract.return_value = [rule_cand]

    # LLM extractor returns a different category/severity
    llm_cand = RiskCandidate(
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        risk_description="Supply chain delay.",
        category="OPERATIONAL",
        severity="MEDIUM",
        source_chunk_id="chunk-1",
        source_text="Supply chain delay.",
        method="LLM_BASED",
        raw_confidence=0.9,
        section_match=True
    )
    llm_mock.extract.return_value = [llm_cand]

    extractor = HybridRiskExtractor(
        rule_extractor=rule_mock,
        llm_extractor=llm_mock
    )

    result = extractor.extract([RiskChunkInput(
        chunk_id="chunk-1",
        text="Supply chain delay.",
        normalized_section_name="Risk Factors",
        fiscal_year=2026,
        fiscal_quarter=1
    )])

    assert len(result.risks) == 1
    risk = result.risks[0]
    # Falls back to RULE values and category
    assert risk.extraction_method == "RULE_BASED"
    assert risk.category == "SUPPLY_CHAIN"
    assert risk.severity == "HIGH"
    assert risk.confidence_score == 0.45  # Disagreement penalty
    assert result.stats.disagreements == 1
