"""Deterministic growth calculations (Phase 3B, task §4).

Pure arithmetic over stored Decimal values — NEVER an LLM (ADR-007/ADR-018).

Formulas:
    absolute_change   = current - previous
    percentage_change = ((current - previous) / previous) * 100   (rounded 2 dp)

Edge-case behavior (documented):
    * missing value (current or previous is None) → both changes None, flag "missing_value".
    * previous == 0 → percentage_change None (division by zero), flag "division_by_zero";
      absolute_change is still current - 0 = current.
    * previous < 0 → percentage_change is computed with the literal formula (signed base),
      flagged "negative_base" so consumers know the sign may be counter-intuitive.
    * non-finite inputs/results → flag "non_finite" (the validator drops these).
"""

from __future__ import annotations

from decimal import Decimal, DivisionByZero, InvalidOperation

from app.financial.comparison.comparison_models import ChangeResult

_PCT_QUANT = Decimal("0.01")


def _finite(d: Decimal | None) -> bool:
    return isinstance(d, Decimal) and d.is_finite()


def compute_changes(current: Decimal | None, previous: Decimal | None) -> ChangeResult:
    if current is None or previous is None:
        return ChangeResult(None, None, ["missing_value"])
    if not _finite(current) or not _finite(previous):
        return ChangeResult(None, None, ["non_finite"])

    absolute = current - previous
    flags: list[str] = []

    if previous == 0:
        return ChangeResult(absolute, None, ["division_by_zero"])

    if previous < 0:
        flags.append("negative_base")

    try:
        percentage = ((current - previous) / previous * Decimal(100)).quantize(_PCT_QUANT)
    except (DivisionByZero, InvalidOperation):  # pragma: no cover - guarded above
        return ChangeResult(absolute, None, ["non_finite"])

    if not percentage.is_finite():
        return ChangeResult(absolute, None, flags + ["non_finite"])
    return ChangeResult(absolute, percentage, flags)
