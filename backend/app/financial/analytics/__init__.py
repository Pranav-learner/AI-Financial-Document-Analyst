"""Financial Analytics Module."""

from app.financial.analytics.exceptions import (
    AnalyticsError,
    ValidationError,
    CalculationError,
)
from app.financial.analytics.analytics_models import (
    CalculatedRatio,
    GeneratedSignal,
)
from app.financial.analytics.ratio_calculator import RatioCalculator
from app.financial.analytics.trend_classifier import TrendClassifier
from app.financial.analytics.signal_generator import SignalGenerator
from app.financial.analytics.analytics_validator import AnalyticsValidator
from app.financial.analytics.analytics_builder import AnalyticsBuilder

__all__ = [
    "AnalyticsError",
    "ValidationError",
    "CalculationError",
    "CalculatedRatio",
    "GeneratedSignal",
    "RatioCalculator",
    "TrendClassifier",
    "SignalGenerator",
    "AnalyticsValidator",
    "AnalyticsBuilder",
]
