"""Validation logic for Competitor Benchmarking configurations (Phase 8)."""

from __future__ import annotations

import uuid
from typing import Any

from app.benchmarking.exceptions import InsufficientCompaniesError, InvalidWeightConfigError


class BenchmarkValidator:
    """Validates benchmark execution configuration and inputs."""

    @staticmethod
    def validate_cohort(company_ids: list[uuid.UUID]) -> None:
        """Ensure cohort size is valid."""
        if not company_ids or len(company_ids) < 2:
            raise InsufficientCompaniesError(
                f"Benchmarking requires a cohort of at least 2 companies, got {len(company_ids) if company_ids else 0}"
            )

        # Check for duplicates
        if len(set(company_ids)) != len(company_ids):
            raise InsufficientCompaniesError(
                "Duplicate company IDs are not allowed in the benchmarking cohort"
            )

    @staticmethod
    def validate_weights(weights: dict[str, float] | None) -> dict[str, float]:
        """Validate and return normalized weights.

        Default weights:
          - financial: 0.40
          - risk: 0.25
          - tone: 0.15
          - capital_allocation: 0.20
        """
        defaults = {
            "financial": 0.40,
            "risk": 0.25,
            "tone": 0.15,
            "capital_allocation": 0.20,
        }

        if weights is None:
            return defaults

        # Normalize keys to lowercase
        norm_weights = {k.lower(): float(v) for k, v in weights.items()}

        # Verify keys
        required_keys = {"financial", "risk", "tone", "capital_allocation"}
        if not required_keys.issubset(norm_weights.keys()):
            # Fill in missing keys if possible, or error out
            for k in required_keys:
                if k not in norm_weights:
                    norm_weights[k] = 0.0

        # Sum validation
        total = sum(norm_weights[k] for k in required_keys)
        # We accept either summing to 1.0 or 100.
        if abs(total - 1.0) > 1e-5 and abs(total - 100.0) > 1e-5:
            raise InvalidWeightConfigError(
                f"Benchmark weights must sum to 1.0 or 100%, got sum={total}"
            )

        # Normalize to 1.0 internally
        if abs(total - 100.0) <= 1e-5:
            norm_weights = {k: v / 100.0 for k, v in norm_weights.items()}

        # Ensure no negative weights
        for k, v in norm_weights.items():
            if v < 0.0:
                raise InvalidWeightConfigError(f"Weight for '{k}' cannot be negative, got {v}")

        return {k: norm_weights[k] for k in required_keys}
