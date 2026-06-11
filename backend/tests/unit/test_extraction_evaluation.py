"""Unit tests for the extraction evaluation framework (Phase 3A)."""

from __future__ import annotations

import pytest
from app.financial.extraction.evaluation import ExtractionEvaluator, load_gold_dataset


@pytest.mark.unit
def test_gold_dataset_loads() -> None:
    gold = load_gold_dataset()
    assert len(gold) >= 6
    assert all(ex.expected for ex in gold)


@pytest.mark.unit
def test_rule_extraction_meets_accuracy_bar() -> None:
    report = ExtractionEvaluator().evaluate(load_gold_dataset())
    # Deterministic rule extraction should nail the gold set.
    assert report.extraction_accuracy >= 0.9
    assert report.precision >= 0.9
    assert report.normalization_accuracy >= 0.9
    assert report.validation_failure_rate == 0.0


@pytest.mark.unit
def test_report_serializes() -> None:
    report = ExtractionEvaluator().evaluate(load_gold_dataset())
    d = report.as_dict()
    assert "extraction_accuracy" in d and "per_metric" in d
    assert d["per_metric"]["REVENUE"]["correct"] >= 1
