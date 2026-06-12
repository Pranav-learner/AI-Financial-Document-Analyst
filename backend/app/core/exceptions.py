"""Domain exceptions + a consistent HTTP error envelope.

Services raise these domain errors (they never speak HTTP). The API layer
registers handlers (see app.main) that translate them into the standard error
response shape from docs/04_API_DESIGN.md §5:

    {"error": {"code": ..., "message": ..., "details": ..., "request_id": ...}}
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base application error carrying an HTTP status, machine code, and message."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class UnsupportedFileTypeError(AppError):
    status_code = 422
    code = "UNSUPPORTED_FILE_TYPE"


class FileTooLargeError(AppError):
    status_code = 413
    code = "FILE_TOO_LARGE"


class EmptyFileError(AppError):
    status_code = 422
    code = "EMPTY_FILE"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class PdfParseError(AppError):
    """Raised by the PDF parser when a document cannot be read."""

    status_code = 422
    code = "PDF_PARSE_ERROR"


class AuthenticationError(AppError):
    """Raised when authentication credentials fail or are invalid."""

    status_code = 401
    code = "AUTHENTICATION_ERROR"


class ForbiddenError(AppError):
    """Raised when permissions are insufficient."""

    status_code = 403
    code = "FORBIDDEN"


class DuplicateUserError(AppError):
    """Raised when registering a user with an already existing email."""

    status_code = 409
    code = "DUPLICATE_USER"

