"""Domain exceptions for Competitor Benchmarking (Phase 8)."""

from __future__ import annotations

from app.core.exceptions import AppError, NotFoundError, ValidationError


class BenchmarkEngineError(AppError):
    """Base exception for all competitor benchmarking engine errors."""

    status_code = 500
    code = "BENCHMARK_ENGINE_ERROR"


class InsufficientCompaniesError(ValidationError):
    """Raised when there are not enough companies to run a benchmark cohort."""

    code = "INSUFFICIENT_COMPANIES"


class MissingReportError(NotFoundError):
    """Raised when a company does not have the required reports for benchmarking."""

    code = "MISSING_REPORT"


class CompanyNotFoundError(NotFoundError):
    """Raised when a requested company ID does not exist (client error, HTTP 404)."""

    code = "COMPANY_NOT_FOUND"


class InvalidWeightConfigError(ValidationError):
    """Raised when benchmarking dimension weight configurations are invalid."""

    code = "INVALID_WEIGHT_CONFIG"
