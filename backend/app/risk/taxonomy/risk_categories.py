"""Risk category taxonomy (Phase 4).

Loads the canonical risk categories + keyword sets from an external JSON file
(risk_categories.json) so the taxonomy is configurable without code changes.
Categories are the top-level grouping for extracted risks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger

log = get_logger(__name__)

_TAXONOMY_JSON = Path(__file__).parent / "risk_categories.json"

_VALID_CATEGORIES = {
    "SUPPLY_CHAIN", "REGULATORY", "MARKET", "COMPETITION", "TECHNOLOGY",
    "CYBERSECURITY", "OPERATIONAL", "LIQUIDITY", "GEOPOLITICAL", "LEGAL",
    "ENVIRONMENTAL", "REPUTATION", "MACROECONOMIC", "OTHER",
}


@dataclass(frozen=True)
class RiskCategoryDef:
    """Definition for a canonical risk category."""

    name: str
    display_name: str
    description: str
    keywords: list[str] = field(default_factory=list)


class RiskTaxonomy:
    """Loaded risk category definitions + keyword→category lookup."""

    def __init__(self, categories: dict[str, RiskCategoryDef]) -> None:
        self._categories = categories
        # Build keyword → category lookup, longest-first for substring matching.
        self._keyword_to_category: list[tuple[str, str]] = []
        for cat_name, cat_def in categories.items():
            for kw in cat_def.keywords:
                self._keyword_to_category.append((kw.lower(), cat_name))
        self._keyword_to_category.sort(key=lambda x: len(x[0]), reverse=True)

    def get(self, name: str) -> RiskCategoryDef | None:
        return self._categories.get(name)

    def all_categories(self) -> list[str]:
        return list(self._categories.keys())

    def classify_by_keywords(self, text: str) -> str | None:
        """Return the best matching category for text, or None."""
        text_lower = text.lower()
        for keyword, category in self._keyword_to_category:
            if keyword in text_lower:
                return category
        return None

    def classify_by_keywords_all(self, text: str) -> list[str]:
        """Return all matching categories for text, ranked by keyword length."""
        text_lower = text.lower()
        seen: set[str] = set()
        result: list[str] = []
        for keyword, category in self._keyword_to_category:
            if keyword in text_lower and category not in seen:
                seen.add(category)
                result.append(category)
        return result


def load_taxonomy(path: Path | None = None) -> RiskTaxonomy:
    """Load taxonomy from JSON."""
    json_path = path or _TAXONOMY_JSON
    with open(json_path) as f:
        data = json.load(f)

    categories: dict[str, RiskCategoryDef] = {}
    for name, defn in data.get("categories", {}).items():
        if name not in _VALID_CATEGORIES:
            log.warning("risk_taxonomy.unknown_category", category=name)
            continue
        categories[name] = RiskCategoryDef(
            name=name,
            display_name=defn.get("display_name", name),
            description=defn.get("description", ""),
            keywords=defn.get("keywords", []),
        )
    return RiskTaxonomy(categories)


_CACHED: RiskTaxonomy | None = None


def get_risk_taxonomy() -> RiskTaxonomy:
    """Singleton accessor."""
    global _CACHED  # noqa: PLW0603
    if _CACHED is None:
        _CACHED = load_taxonomy()
    return _CACHED
