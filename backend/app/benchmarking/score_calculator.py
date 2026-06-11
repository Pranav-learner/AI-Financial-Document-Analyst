"""Score calculator for normalizing metrics and computing weighted dimension scores (Phase 8)."""

from __future__ import annotations

from typing import Any


class ScoreCalculator:
    """Normalizes raw metric values and computes weighted dimension/overall scores."""

    @staticmethod
    def normalize_metrics(
        items: list[tuple[Any, float | None]],
        higher_is_better: bool = True,
    ) -> list[tuple[Any, float | None]]:
        """Normalize raw metric values to a 0-100 range based on the cohort min/max.

        Missing values remain None.
        If all valid values are identical, they all receive a score of 100.0.
        """
        valid_vals = [v for _, v in items if v is not None]
        if not valid_vals:
            return [(k, None) for k, _ in items]

        min_val = min(valid_vals)
        max_val = max(valid_vals)

        scores: dict[Any, float | None] = {}
        for k, v in items:
            if v is None:
                scores[k] = None
            elif abs(max_val - min_val) < 1e-9:
                scores[k] = 100.0
            else:
                if higher_is_better:
                    scores[k] = ((v - min_val) / (max_val - min_val)) * 100.0
                else:
                    scores[k] = ((max_val - v) / (max_val - min_val)) * 100.0

        return [(k, scores[k]) for k, _ in items]

    @staticmethod
    def calculate_dimension_score(metric_scores: list[float]) -> float | None:
        """Compute dimension score as the simple average of present metric scores."""
        valid_scores = [s for s in metric_scores if s is not None]
        if not valid_scores:
            return None
        return sum(valid_scores) / len(valid_scores)

    @staticmethod
    def calculate_overall_score(
        dimension_scores: dict[str, float | None],
        weights: dict[str, float],
    ) -> float | None:
        """Compute the weighted overall score from dimension scores.

        Gracefully handles missing dimensions by dynamically reallocating weights
        proportionally among present dimensions.
        """
        weighted_sum = 0.0
        weight_sum = 0.0

        for dim, score in dimension_scores.items():
            if score is not None:
                w = weights.get(dim.lower(), 0.0)
                weighted_sum += score * w
                weight_sum += w

        if weight_sum < 1e-9:
            return None

        return weighted_sum / weight_sum
