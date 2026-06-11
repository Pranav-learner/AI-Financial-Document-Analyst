"""Unit tests for the risk evaluation frameworks (Phase 4)."""

from __future__ import annotations

import pytest
from app.risk.extraction.evaluation import RiskExtractionEvaluator, load_gold_dataset as load_extraction_gold
from app.risk.evolution.evaluation import RiskEvolutionEvaluator, load_gold_dataset as load_evolution_gold


@pytest.mark.unit
def test_risk_extraction_gold_dataset_loads() -> None:
    gold = load_extraction_gold()
    assert len(gold) >= 5
    assert all(ex.expected for ex in gold)


@pytest.mark.unit
def test_risk_extraction_evaluator() -> None:
    report = RiskExtractionEvaluator().evaluate(load_extraction_gold())
    # The rule-based extraction on the gold dataset should meet accuracy/precision bars.
    assert report.recall >= 0.8
    assert report.precision >= 0.5
    assert report.category_accuracy >= 0.8
    assert report.severity_accuracy >= 0.8
    assert report.validation_failure_rate == 0.0


@pytest.mark.unit
def test_risk_evolution_gold_dataset_loads() -> None:
    gold = load_evolution_gold()
    assert len(gold) >= 5
    assert all(ex.expected for ex in gold)


@pytest.mark.unit
def test_risk_evolution_evaluator() -> None:
    report = RiskEvolutionEvaluator().evaluate(load_evolution_gold())
    # The classification on the gold dataset should match exactly.
    assert report.accuracy == 1.0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert "ESCALATED_RISK" in report.per_evolution_type
