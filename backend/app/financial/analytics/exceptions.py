"""Financial Analytics Exception Classes."""

class AnalyticsError(Exception):
    """Base exception for all financial analytics errors."""
    pass


class ValidationError(AnalyticsError):
    """Raised when the calculated ratios or signals fail validation."""
    pass


class CalculationError(AnalyticsError):
    """Raised when there is an error calculating a ratio or generating a signal."""
    pass
