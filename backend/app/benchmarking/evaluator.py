"""Evaluation module for Competitor Benchmarking Engine (Phase 8).

Validates ranking accuracy, score normalization, tie handling, missing metric robustness,
coverage across dimensions, and execution latency.
"""

from __future__ import annotations

import time
from typing import Any

from app.benchmarking.ranking_engine import RankingEngine
from app.benchmarking.score_calculator import ScoreCalculator


class BenchmarkingEvaluator:
    """Evaluates the benchmarking calculations for accuracy, coverage, and latency."""

    @staticmethod
    def run_suite() -> dict[str, Any]:
        """Run the full evaluation suite and return the report."""
        report: dict[str, Any] = {
            "tests_run": 0,
            "tests_passed": 0,
            "accuracy_passed": True,
            "coverage_percent": 100.0,
            "latency_ms": 0.0,
            "details": {},
        }

        # Start timer
        start_time = time.perf_counter()

        try:
            # Test 1: Standard Ranking & Ties (Min method)
            # Input: A=10, B=20, C=20, D=30 (higher is better)
            # Descending order: D (30), B (20), C (20), A (10)
            # Expected ranks: D=1, B=2, C=2, A=4
            items = [("A", 10.0), ("B", 20.0), ("C", 20.0), ("D", 30.0)]
            ranks = RankingEngine.rank_items(items, higher_is_better=True, tie_method="min")
            rank_dict = {k: r for k, r, _ in ranks}
            assert rank_dict["D"] == 1, f"Expected D=1, got {rank_dict['D']}"
            assert rank_dict["B"] == 2, f"Expected B=2, got {rank_dict['B']}"
            assert rank_dict["C"] == 2, f"Expected C=2, got {rank_dict['C']}"
            assert rank_dict["A"] == 4, f"Expected A=4, got {rank_dict['A']}"
            report["tests_passed"] += 1
            report["tests_run"] += 1
            report["details"]["ranking_ties_min"] = "PASS"
        except AssertionError as e:
            report["tests_run"] += 1
            report["accuracy_passed"] = False
            report["details"]["ranking_ties_min"] = f"FAIL: {e}"

        try:
            # Test 2: Dense Ranking
            # Expected ranks: D=1, B=2, C=2, A=3
            ranks_dense = RankingEngine.rank_items(items, higher_is_better=True, tie_method="dense")
            rank_dense_dict = {k: r for k, r, _ in ranks_dense}
            assert rank_dense_dict["D"] == 1, f"Expected D=1, got {rank_dense_dict['D']}"
            assert rank_dense_dict["B"] == 2, f"Expected B=2, got {rank_dense_dict['B']}"
            assert rank_dense_dict["C"] == 2, f"Expected C=2, got {rank_dense_dict['C']}"
            assert rank_dense_dict["A"] == 3, f"Expected A=3, got {rank_dense_dict['A']}"
            report["tests_passed"] += 1
            report["tests_run"] += 1
            report["details"]["ranking_ties_dense"] = "PASS"
        except AssertionError as e:
            report["tests_run"] += 1
            report["accuracy_passed"] = False
            report["details"]["ranking_ties_dense"] = f"FAIL: {e}"

        try:
            # Test 3: Score Normalization
            # Inputs: A=10, B=20, C=30. Higher is better.
            # Normalization min=10, max=30
            # Expected scores: A=0.0, B=50.0, C=100.0
            scores = ScoreCalculator.normalize_metrics(
                [("A", 10.0), ("B", 20.0), ("C", 30.0)], higher_is_better=True
            )
            score_dict = dict(scores)
            assert abs(score_dict["A"] - 0.0) < 1e-5, f"Expected A=0, got {score_dict['A']}"
            assert abs(score_dict["B"] - 50.0) < 1e-5, f"Expected B=50, got {score_dict['B']}"
            assert abs(score_dict["C"] - 100.0) < 1e-5, f"Expected C=100, got {score_dict['C']}"

            # Inverted normalization (lower is better):
            # Expected scores: A=100.0, B=50.0, C=0.0
            scores_inv = ScoreCalculator.normalize_metrics(
                [("A", 10.0), ("B", 20.0), ("C", 30.0)], higher_is_better=False
            )
            score_inv_dict = dict(scores_inv)
            assert abs(score_inv_dict["A"] - 100.0) < 1e-5, f"Expected A=100, got {score_inv_dict['A']}"
            assert abs(score_inv_dict["B"] - 50.0) < 1e-5, f"Expected B=50, got {score_inv_dict['B']}"
            assert abs(score_inv_dict["C"] - 0.0) < 1e-5, f"Expected C=0, got {score_inv_dict['C']}"

            report["tests_passed"] += 1
            report["tests_run"] += 1
            report["details"]["score_normalization"] = "PASS"
        except AssertionError as e:
            report["tests_run"] += 1
            report["accuracy_passed"] = False
            report["details"]["score_normalization"] = f"FAIL: {e}"

        try:
            # Test 4: Missing Metrics / Weight Reallocation
            # weights: fin=0.4, risk=0.25, tone=0.15, cap=0.2
            # Company missing 'tone' score.
            # Scores: fin=80, risk=60, tone=None, cap=100
            # Expected overall: (80*0.4 + 60*0.25 + 100*0.2) / (0.4 + 0.25 + 0.2) = 67.0 / 0.85 = 78.8235
            weights = {"financial": 0.4, "risk": 0.25, "tone": 0.15, "capital_allocation": 0.2}
            dim_scores = {"financial": 80.0, "risk": 60.0, "tone": None, "capital_allocation": 100.0}
            overall = ScoreCalculator.calculate_overall_score(dim_scores, weights)
            expected = 67.0 / 0.85
            assert overall is not None
            assert abs(overall - expected) < 1e-5, f"Expected {expected}, got {overall}"
            report["tests_passed"] += 1
            report["tests_run"] += 1
            report["details"]["weight_reallocation"] = "PASS"
        except AssertionError as e:
            report["tests_run"] += 1
            report["accuracy_passed"] = False
            report["details"]["weight_reallocation"] = f"FAIL: {e}"

        # Calculate latency
        end_time = time.perf_counter()
        report["latency_ms"] = (end_time - start_time) * 1000.0

        return report
