"""Risk normalization utilities (Phase 4).

Normalize risk names, categories, and descriptions to canonical forms before
storage. Deterministic — no LLM involvement.
"""

from __future__ import annotations

import re

from app.risk.taxonomy.risk_aliases import resolve_risk_alias
from app.risk.taxonomy.risk_categories import RiskTaxonomy, get_risk_taxonomy

_VALID_CATEGORIES = {
    "SUPPLY_CHAIN", "REGULATORY", "MARKET", "COMPETITION", "TECHNOLOGY",
    "CYBERSECURITY", "OPERATIONAL", "LIQUIDITY", "GEOPOLITICAL", "LEGAL",
    "ENVIRONMENTAL", "REPUTATION", "MACROECONOMIC", "OTHER",
}

_WS = re.compile(r"\s+")


def normalize_risk_name(name: str) -> str:
    """Normalize a risk name to its canonical form."""
    return resolve_risk_alias(name)


def normalize_category(
    category: str | None,
    risk_text: str = "",
    taxonomy: RiskTaxonomy | None = None,
) -> str:
    """Normalize a category string to a valid canonical category.

    If the given category is already valid, return it. Otherwise, attempt
    keyword-based classification from the risk text. Falls back to OTHER.
    """
    if category and category.upper() in _VALID_CATEGORIES:
        return category.upper()

    tax = taxonomy or get_risk_taxonomy()
    inferred = tax.classify_by_keywords(risk_text)
    return inferred if inferred else "OTHER"


def normalize_description(description: str) -> str:
    """Clean up a risk description: collapse whitespace, strip."""
    return _WS.sub(" ", description.strip())


def normalize_severity(severity: str) -> str:
    """Normalize severity to one of LOW/MEDIUM/HIGH/CRITICAL."""
    s = severity.strip().upper()
    if s in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        return s
    return "MEDIUM"  # safe default
