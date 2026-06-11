"""Period matching (Phase 3B, task §3).

Deterministically maps a current fiscal period to its comparison counterpart:

    YOY:  FY2024 ↔ FY2023 ;  Q1 2025 ↔ Q1 2024  (same quarter, prior year)
    QOQ:  Q2 2025 ↔ Q1 2025 ;  Q1 2025 ↔ Q4 2024 (prior quarter; wraps a year)

QoQ requires a quarter (annual reports have none → no QoQ). YTD/TTM are reserved
(not generated in 3B). Missing / duplicate / incomplete periods are handled by the
service (a missing counterpart simply yields no comparison).
"""

from __future__ import annotations

from app.models.enums import ComparisonType

Period = tuple[int | None, int | None]   # (fiscal_year, fiscal_quarter)


class PeriodMatcher:
    @staticmethod
    def previous_period(comparison_type: str, year: int | None, quarter: int | None) -> Period | None:
        if comparison_type == ComparisonType.YOY.value:
            if year is None:
                return None
            return (year - 1, quarter)   # quarter may be None (annual)
        if comparison_type == ComparisonType.QOQ.value:
            if year is None or quarter is None:
                return None              # QoQ needs a quarter
            if quarter == 1:
                return (year - 1, 4)     # wrap to Q4 of the prior year
            return (year, quarter - 1)
        return None                       # YTD / TTM not generated in 3B

    @staticmethod
    def format_period(year: int | None, quarter: int | None) -> str:
        if year is None:
            return "UNKNOWN"
        return f"Q{quarter} {year}" if quarter else f"FY{year}"
