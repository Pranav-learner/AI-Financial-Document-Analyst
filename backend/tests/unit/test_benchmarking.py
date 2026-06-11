"""Unit tests for Competitor Benchmarking Engine (Phase 8)."""

from __future__ import annotations

import uuid
import pytest

from app.benchmarking.exceptions import InsufficientCompaniesError, InvalidWeightConfigError
from app.benchmarking.ranking_engine import RankingEngine
from app.benchmarking.score_calculator import ScoreCalculator
from app.benchmarking.validators import BenchmarkValidator
from app.benchmarking.evaluator import BenchmarkingEvaluator


@pytest.mark.unit
def test_ranking_engine_sorting_descending() -> None:
    """Test ranking where higher values are better (default)."""
    items = [("A", 10.0), ("B", 30.0), ("C", 20.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=True)
    rank_dict = {k: r for k, r, _ in ranks}
    assert rank_dict["B"] == 1
    assert rank_dict["C"] == 2
    assert rank_dict["A"] == 3


@pytest.mark.unit
def test_ranking_engine_sorting_ascending() -> None:
    """Test ranking where lower values are better."""
    items = [("A", 10.0), ("B", 30.0), ("C", 20.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=False)
    rank_dict = {k: r for k, r, _ in ranks}
    assert rank_dict["A"] == 1
    assert rank_dict["C"] == 2
    assert rank_dict["B"] == 3


@pytest.mark.unit
def test_ranking_engine_tie_handling_min() -> None:
    """Test standard competition tie-breaking (min)."""
    items = [("A", 10.0), ("B", 30.0), ("C", 30.0), ("D", 40.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=True, tie_method="min")
    rank_dict = {k: r for k, r, _ in ranks}
    assert rank_dict["D"] == 1
    assert rank_dict["B"] == 2
    assert rank_dict["C"] == 2
    assert rank_dict["A"] == 4  # Skips 3 due to tie at 2


@pytest.mark.unit
def test_ranking_engine_tie_handling_dense() -> None:
    """Test dense ranking tie-breaking."""
    items = [("A", 10.0), ("B", 30.0), ("C", 30.0), ("D", 40.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=True, tie_method="dense")
    rank_dict = {k: r for k, r, _ in ranks}
    assert rank_dict["D"] == 1
    assert rank_dict["B"] == 2
    assert rank_dict["C"] == 2
    assert rank_dict["A"] == 3  # Next sequential rank is 3


@pytest.mark.unit
def test_ranking_engine_tie_handling_average() -> None:
    """Test average ranking tie-breaking."""
    items = [("A", 10.0), ("B", 30.0), ("C", 30.0), ("D", 40.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=True, tie_method="average")
    rank_dict = {k: r for k, r, _ in ranks}
    assert rank_dict["D"] == 1
    assert rank_dict["B"] == 2.5  # Average of 2 and 3
    assert rank_dict["C"] == 2.5
    assert rank_dict["A"] == 4


@pytest.mark.unit
def test_ranking_engine_missing_data() -> None:
    """Test that missing data is placed at the end with None rank and percentile."""
    items = [("A", 10.0), ("B", None), ("C", 20.0)]
    ranks = RankingEngine.rank_items(items, higher_is_better=True)
    rank_dict = {k: (r, p) for k, r, p in ranks}
    assert rank_dict["C"][0] == 1
    assert rank_dict["A"][0] == 2
    assert rank_dict["B"][0] is None
    assert rank_dict["B"][1] is None


@pytest.mark.unit
def test_score_calculator_normalization() -> None:
    """Test basic min-max score normalization."""
    items = [("A", 10.0), ("B", 20.0), ("C", 30.0)]
    scores = ScoreCalculator.normalize_metrics(items, higher_is_better=True)
    score_dict = dict(scores)
    assert abs(score_dict["A"] - 0.0) < 1e-5
    assert abs(score_dict["B"] - 50.0) < 1e-5
    assert abs(score_dict["C"] - 100.0) < 1e-5


@pytest.mark.unit
def test_score_calculator_normalization_inverted() -> None:
    """Test min-max normalization when lower values are better."""
    items = [("A", 10.0), ("B", 20.0), ("C", 30.0)]
    scores = ScoreCalculator.normalize_metrics(items, higher_is_better=False)
    score_dict = dict(scores)
    assert abs(score_dict["A"] - 100.0) < 1e-5
    assert abs(score_dict["B"] - 50.0) < 1e-5
    assert abs(score_dict["C"] - 0.0) < 1e-5


@pytest.mark.unit
def test_score_calculator_identical_values() -> None:
    """Test normalization when all values in cohort are identical."""
    items = [("A", 15.0), ("B", 15.0), ("C", 15.0)]
    scores = ScoreCalculator.normalize_metrics(items, higher_is_better=True)
    score_dict = dict(scores)
    assert score_dict["A"] == 100.0
    assert score_dict["B"] == 100.0
    assert score_dict["C"] == 100.0


@pytest.mark.unit
def test_score_calculator_overall_weighted_score() -> None:
    """Test overall score calculation and dynamic weight reallocation."""
    weights = {"financial": 0.40, "risk": 0.25, "tone": 0.15, "capital_allocation": 0.20}
    dim_scores = {"financial": 80.0, "risk": 60.0, "tone": 70.0, "capital_allocation": 100.0}
    
    # 1. Full scores
    overall = ScoreCalculator.calculate_overall_score(dim_scores, weights)
    expected = (80.0*0.40 + 60.0*0.25 + 70.0*0.15 + 100.0*0.20)  # 32 + 15 + 10.5 + 20 = 77.5
    assert abs(overall - expected) < 1e-5

    # 2. Missing tone dimension (weight 0.15)
    dim_scores_missing = {"financial": 80.0, "risk": 60.0, "tone": None, "capital_allocation": 100.0}
    overall_missing = ScoreCalculator.calculate_overall_score(dim_scores_missing, weights)
    expected_missing = (80.0*0.40 + 60.0*0.25 + 100.0*0.20) / (0.40 + 0.25 + 0.20)  # 67.0 / 0.85 = 78.8235
    assert abs(overall_missing - expected_missing) < 1e-5


@pytest.mark.unit
def test_validator_cohort_checks() -> None:
    """Test validation of company cohorts."""
    # Empty cohort
    with pytest.raises(InsufficientCompaniesError):
        BenchmarkValidator.validate_cohort([])

    # Only 1 company
    with pytest.raises(InsufficientCompaniesError):
        BenchmarkValidator.validate_cohort([uuid.uuid4()])

    # Duplicate companies
    cid = uuid.uuid4()
    with pytest.raises(InsufficientCompaniesError):
        BenchmarkValidator.validate_cohort([cid, cid])


@pytest.mark.unit
def test_validator_weights() -> None:
    """Test weight config validation and normalization."""
    # Sum to 1.0
    weights = {"financial": 0.5, "risk": 0.2, "tone": 0.2, "capital_allocation": 0.1}
    validated = BenchmarkValidator.validate_weights(weights)
    assert validated["financial"] == 0.5
    assert validated["capital_allocation"] == 0.1

    # Sum to 100
    weights_pct = {"financial": 50, "risk": 20, "tone": 20, "capital_allocation": 10}
    validated_pct = BenchmarkValidator.validate_weights(weights_pct)
    assert abs(validated_pct["financial"] - 0.5) < 1e-5

    with pytest.raises(InvalidWeightConfigError):
        BenchmarkValidator.validate_weights({"financial": 0.5, "risk": 0.3})

    # Negative weight
    with pytest.raises(InvalidWeightConfigError):
        BenchmarkValidator.validate_weights({"financial": 1.2, "risk": -0.2, "tone": 0.0, "capital_allocation": 0.0})


@pytest.mark.unit
def test_evaluator_runs_completely() -> None:
    """Run the evaluation suite as part of unit tests."""
    report = BenchmarkingEvaluator.run_suite()
    assert report["tests_run"] == 4
    assert report["tests_passed"] == 4
    assert report["accuracy_passed"] is True
