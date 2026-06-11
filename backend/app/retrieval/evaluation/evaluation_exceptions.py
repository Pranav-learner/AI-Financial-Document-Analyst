"""Retrieval-evaluation exceptions (Phase 2D)."""

from __future__ import annotations

from app.core.exceptions import AppError


class EvaluationError(AppError):
    status_code = 500
    code = "EVALUATION_ERROR"


class GroundTruthError(EvaluationError):
    """The ground-truth dataset is missing, malformed, or empty."""

    status_code = 500
    code = "GROUND_TRUTH_ERROR"


class UnknownBenchmarkError(EvaluationError):
    status_code = 404
    code = "UNKNOWN_BENCHMARK"


class InvalidEvaluationRequestError(EvaluationError):
    status_code = 422
    code = "INVALID_EVALUATION_REQUEST"
