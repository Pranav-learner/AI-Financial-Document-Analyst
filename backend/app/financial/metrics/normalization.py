"""Deterministic value normalization (Phase 3A, task §9).

Parses financial value expressions into a canonical form, with NO LLM involvement
— this is the deterministic backbone that every extracted number must pass:

    "$96.7 billion"   -> value 96700000000, currency USD, unit BILLION
    "$96,700 million" -> value 96700000000, currency USD, unit MILLION (same value)
    "28.5%"           -> value 28.5,        currency None, unit PERCENT
    "(1,234) million" -> value -1234000000, currency None, unit MILLION

`value` is the absolute magnitude (scaled), so two differently-expressed amounts
normalize to the *same* number — the property comparisons depend on later.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CURRENCY_CODES = {
    "usd": "USD", "us$": "USD", "eur": "EUR", "gbp": "GBP",
    "jpy": "JPY", "cad": "CAD", "aud": "AUD", "cny": "CNY", "rmb": "CNY",
}
_SCALE_FACTOR = {
    "thousand": Decimal(10) ** 3, "k": Decimal(10) ** 3,
    "million": Decimal(10) ** 6, "mm": Decimal(10) ** 6, "mn": Decimal(10) ** 6,
    "m": Decimal(10) ** 6,
    "billion": Decimal(10) ** 9, "bn": Decimal(10) ** 9, "b": Decimal(10) ** 9,
    "trillion": Decimal(10) ** 12, "tn": Decimal(10) ** 12, "t": Decimal(10) ** 12,
}
_SCALE_LABEL = {
    "thousand": "THOUSAND", "k": "THOUSAND",
    "million": "MILLION", "mm": "MILLION", "mn": "MILLION", "m": "MILLION",
    "billion": "BILLION", "bn": "BILLION", "b": "BILLION",
    "trillion": "TRILLION", "tn": "TRILLION", "t": "TRILLION",
}

# A monetary / numeric value with optional currency, scale, percent, and sign.
_VALUE_RE = re.compile(
    r"""
    (?P<paren>\()?\s*
    (?P<cur>US\$|\$|€|£|¥|USD|EUR|GBP|JPY|CAD|AUD|CNY|RMB)?\s*
    (?P<sign>-)?\s*
    (?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+)
    (?:
        (?P<scale_attached>bn|mn|mm|[kmbt])\b
      | \s+(?P<scale_word>thousand|million|billion|trillion)s?\b
    )?
    \s*(?P<pct>%|percent\b)?
    \s*(?P<paren_close>\))?
    """,
    re.IGNORECASE | re.VERBOSE,
)


@dataclass(frozen=True)
class NormalizedValue:
    value: Decimal             # signed absolute magnitude (scaled), or percent number
    currency: str | None
    unit: str                  # ABSOLUTE / THOUSAND / MILLION / BILLION / TRILLION / PERCENT
    is_percent: bool
    has_currency_or_scale: bool  # heuristic: real metric values usually do
    raw: str
    start: int
    end: int


def _to_value(m: re.Match) -> NormalizedValue | None:
    try:
        number = Decimal(m.group("num").replace(",", ""))
    except InvalidOperation:  # pragma: no cover - regex guarantees a number
        return None

    cur_raw = m.group("cur")
    currency = None
    if cur_raw:
        currency = _CURRENCY_SYMBOLS.get(cur_raw) or _CURRENCY_CODES.get(cur_raw.lower())

    scale_key = (m.group("scale_attached") or m.group("scale_word") or "").lower()
    is_pct = bool(m.group("pct"))

    if is_pct:
        value, unit = number, "PERCENT"
        currency = None
    elif scale_key:
        value = number * _SCALE_FACTOR[scale_key]
        unit = _SCALE_LABEL[scale_key]
    else:
        value, unit = number, "ABSOLUTE"

    negative = bool(m.group("sign")) or bool(m.group("paren") and m.group("paren_close"))
    if negative:
        value = -value

    return NormalizedValue(
        value=value,
        currency=currency,
        unit=unit,
        is_percent=is_pct,
        has_currency_or_scale=bool(currency or scale_key or is_pct),
        raw=m.group(0).strip(),
        start=m.start(),
        end=m.end(),
    )


def find_values(text: str) -> list[NormalizedValue]:
    """All parseable values in `text`, in order of appearance."""
    out: list[NormalizedValue] = []
    for m in _VALUE_RE.finditer(text):
        v = _to_value(m)
        if v is not None:
            out.append(v)
    return out


def normalize_value(text: str) -> NormalizedValue | None:
    """The first parseable value in `text` (or None)."""
    values = find_values(text)
    return values[0] if values else None


def normalize_currency(symbol_or_code: str | None) -> str | None:
    if not symbol_or_code:
        return None
    s = symbol_or_code.strip()
    return _CURRENCY_SYMBOLS.get(s) or _CURRENCY_CODES.get(s.lower())


# Period parsing (used only as a fallback for an LLM-provided "period" string;
# the authoritative period is the chunk's report year/quarter).
_QUARTER_RE = re.compile(r"\bQ([1-4])\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def parse_period(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    q = _QUARTER_RE.search(text)
    y = _YEAR_RE.search(text)
    return (int(y.group(0)) if y else None, int(q.group(1)) if q else None)
