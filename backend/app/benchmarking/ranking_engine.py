"""Deterministic Ranking Engine with tie handling and percentiles (Phase 8)."""

from __future__ import annotations

from typing import Any, TypeVar

T = TypeVar("T")


class RankingEngine:
    """Computes deterministic ranks and percentiles for cohort metrics."""

    @staticmethod
    def rank_items(
        items: list[tuple[T, float | None]],
        higher_is_better: bool = True,
        tie_method: str = "min",
    ) -> list[tuple[T, int | float | None, float | None]]:
        """Rank a list of items of shape (key, value).

        Handles missing values (None) by placing them at the end with None rank/percentile.
        Handles ties using the specified method:
          - 'min': Standard competition ranking (1, 2, 2, 4)
          - 'dense': Dense ranking (1, 2, 2, 3)
          - 'average': Average ranking (1, 2.5, 2.5, 4)
        """
        # Separate valid values and missing values
        valid_items = [(k, v) for k, v in items if v is not None]
        missing_items = [(k, None) for k, v in items if v is None]

        # Sort valid items
        # True = descending (highest value is rank 1), False = ascending (lowest value is rank 1)
        valid_items.sort(key=lambda x: x[1], reverse=higher_is_better)  # type: ignore

        m = len(valid_items)
        if m == 0:
            return [(k, None, None) for k, _ in items]

        # Group sorted items by value (using 1e-9 tolerance for floats)
        groups: list[tuple[float, list[int]]] = []
        for idx, (k, val) in enumerate(valid_items):
            found_group = False
            for g_val, g_indices in groups:
                if abs(g_val - val) < 1e-9:
                    g_indices.append(idx)
                    found_group = True
                    break
            if not found_group:
                groups.append((val, [idx]))

        # Temporary list to hold ranks
        temp_ranks: list[float] = [0.0] * m

        # Assign ranks to each group
        for group_idx, (g_val, g_indices) in enumerate(groups):
            start_idx = g_indices[0]
            size = len(g_indices)

            if tie_method == "min":
                rank_val = float(start_idx + 1)
            elif tie_method == "dense":
                rank_val = float(group_idx + 1)
            else:  # "average"
                rank_val = sum(i + 1 for i in g_indices) / size

            for idx in g_indices:
                temp_ranks[idx] = rank_val


        # Compute percentiles and construct output
        # Percentile formula: (M - rank + 0.5) / M * 100
        # If higher_is_better is True, rank 1 is highest value, so percentile is highest.
        # If higher_is_better is False, rank 1 is lowest value (which is good), so percentile is also highest.
        results: dict[Any, tuple[int | float | None, float | None]] = {}
        for idx, (k, val) in enumerate(valid_items):
            rank = temp_ranks[idx]
            # Convert rank to int if it's an integer value
            if rank.is_integer():
                rank = int(rank)
            percentile = ((m - rank + 0.5) / m) * 100.0
            # Clip percentile between 0 and 100
            percentile = max(0.0, min(100.0, percentile))
            results[k] = (rank, percentile)

        for k, _ in missing_items:
            results[k] = (None, None)

        # Re-assemble in the original input order to preserve sequence stability
        output: list[tuple[T, int | float | None, float | None]] = []
        for k, _ in items:
            rank, pct = results[k]
            output.append((k, rank, pct))

        return output
