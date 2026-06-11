"""Unit tests for Phase 4 Risk Evolution Engine."""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import MagicMock

from app.models.risk_factor import RiskFactor
from app.risk.evolution.models import RiskMatch, EvolutionResultRow
from app.risk.evolution.risk_matcher import RiskMatcher, calculate_jaccard
from app.risk.evolution.evolution_classifier import RiskEvolutionClassifier
from app.risk.evolution.evolution_service import RiskEvolutionService
from app.risk.evolution.validators import EvolutionValidator


def test_calculate_jaccard():
    assert calculate_jaccard("Supply Chain disruption", "disruption of supply chain") > 0.5
    assert calculate_jaccard("Supply Chain", "Regulatory Changes") == 0.0
    assert calculate_jaccard("Supply Chain", "Supply Chain") == 1.0


def test_risk_matcher():
    pointer = RiskMatcher(fuzzy_threshold=0.4)

    curr_id = uuid.uuid4()
    prev_id = uuid.uuid4()

    curr_risk = RiskFactor(
        id=curr_id,
        risk_name="Supply Chain Disruption",
        normalized_risk_name="supply_chain_disruption",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )
    prev_risk = RiskFactor(
        id=prev_id,
        risk_name="Supply Chain Disruption",
        normalized_risk_name="supply_chain_disruption",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )

    # Exact match test
    matches = pointer.match_risks([curr_risk], [prev_risk])
    assert len(matches) == 1
    assert matches[0].match_type == "EXACT"
    assert matches[0].current_id == str(curr_id)
    assert matches[0].previous_id == str(prev_id)


def test_risk_matcher_fuzzy():
    pointer = RiskMatcher(fuzzy_threshold=0.4)

    curr_id = uuid.uuid4()
    prev_id = uuid.uuid4()

    # Different risk name, but same category and token overlap
    curr_risk = RiskFactor(
        id=curr_id,
        risk_name="Supply Chain Disruption",
        normalized_risk_name="supply_chain_disruption",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )
    prev_risk = RiskFactor(
        id=prev_id,
        risk_name="Supply Chain Issues",
        normalized_risk_name="supply_chain_issues",
        category="SUPPLY_CHAIN",
        severity="MEDIUM",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )

    matches = pointer.match_risks([curr_risk], [prev_risk])
    assert len(matches) == 1
    assert matches[0].match_type == "FUZZY"
    assert matches[0].current_id == str(curr_id)
    assert matches[0].previous_id == str(prev_id)


def test_evolution_classifier():
    classifier = RiskEvolutionClassifier()

    company_id = str(uuid.uuid4())
    curr_id = uuid.uuid4()
    prev_id = uuid.uuid4()

    curr_risk = RiskFactor(
        id=curr_id,
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        category="SUPPLY_CHAIN",
        severity="HIGH",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )
    prev_risk = RiskFactor(
        id=prev_id,
        risk_name="Supply Chain Risk",
        normalized_risk_name="supply_chain_risk",
        category="SUPPLY_CHAIN",
        severity="LOW",
        confidence_score=0.8,
        extraction_method="RULE_BASED",
        source_text="text"
    )

    current_map = {str(curr_id): curr_risk}
    previous_map = {str(prev_id): prev_risk}

    # Low -> High severity = ESCALATED_RISK
    match = RiskMatch(
        current_id=str(curr_id),
        previous_id=str(prev_id),
        current_name="Supply Chain Risk",
        previous_name="Supply Chain Risk",
        category="SUPPLY_CHAIN",
        match_type="EXACT",
        match_score=1.0
    )
    row = classifier.classify(match, company_id, current_map, previous_map)
    assert row.evolution_type == "ESCALATED_RISK"
    assert "escalated from LOW to HIGH severity" in row.explanation

    # Unchanged severity
    prev_risk.severity = "HIGH"
    row = classifier.classify(match, company_id, current_map, previous_map)
    assert row.evolution_type == "UNCHANGED_RISK"

    # High -> Low severity = REDUCED_RISK
    prev_risk.severity = "CRITICAL"
    row = classifier.classify(match, company_id, current_map, previous_map)
    assert row.evolution_type == "REDUCED_RISK"
