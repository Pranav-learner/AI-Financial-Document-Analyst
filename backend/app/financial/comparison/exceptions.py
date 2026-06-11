"""Comparison-engine exceptions (Phase 3B)."""

from __future__ import annotations


class ComparisonError(Exception):
    """Base for period-comparison failures."""


class InvalidPeriodError(ComparisonError):
    """A period reference is missing or malformed."""


class CalculationError(ComparisonError):
    """A deterministic calculation produced an impossible/non-finite result."""
