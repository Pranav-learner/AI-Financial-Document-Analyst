"""Section taxonomy loader (Phase 1B).

Loads the canonical section taxonomy, alias map, SEC item map, transcript markers,
and confidence weights from an external JSON file (configurable via
`SECTION_TAXONOMY_PATH`, defaulting to the packaged `taxonomy.json`).

Detection/normalization logic depends on this object — values are never hardcoded
in business logic, satisfying the "configurable taxonomy" requirement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

_DEFAULT_PATH = Path(__file__).parent / "taxonomy.json"


@dataclass(frozen=True)
class Taxonomy:
    canonical_sections: tuple[str, ...]
    aliases: dict[str, str]                       # lowercased alias -> canonical
    sec_items: dict[str, dict[str, str]]          # group -> {item code -> canonical}
    transcript_markers: dict[str, str]            # lowercased marker -> canonical
    confidence: dict[str, float]
    fallback_section: str
    fallback_confidence: float

    def canonical_for_alias(self, text: str) -> str | None:
        return self.aliases.get(text.strip().lower())

    def item_canonical(self, report_type: str | None, part: str, code: str) -> str | None:
        """Resolve a SEC item code to a canonical section, doc-type/part aware.

        10-Q reuses item numbers across Part I/II, so the current `part` matters;
        10-K item numbers are flat. Unknown types fall back to 10-K then 10-Q-I.
        """
        rt = (report_type or "").upper()
        code = code.strip().upper()
        if rt == "10-Q":
            return (self.sec_items.get(f"10-Q-{part}") or {}).get(code)
        if rt == "10-K":
            return (self.sec_items.get("10-K") or {}).get(code)
        return (self.sec_items.get("10-K") or {}).get(code) or (
            self.sec_items.get("10-Q-I") or {}
        ).get(code)

    def is_canonical(self, name: str) -> bool:
        return name in self.canonical_sections

    def confidence_for(self, kind: str) -> float:
        return float(self.confidence.get(kind, self.confidence.get("weak", 0.5)))


def load_taxonomy(path: str | Path | None = None) -> Taxonomy:
    """Load and validate a taxonomy from JSON."""
    resolved = Path(path or settings.section_taxonomy_path or _DEFAULT_PATH)
    raw = json.loads(resolved.read_text(encoding="utf-8"))

    aliases = {k.strip().lower(): v for k, v in raw.get("aliases", {}).items()}
    sec_items = {
        group: {code.strip().upper(): canon for code, canon in mapping.items()}
        for group, mapping in raw.get("sec_items", {}).items()
    }
    markers = {k.strip().lower(): v for k, v in raw.get("transcript_markers", {}).items()}

    return Taxonomy(
        canonical_sections=tuple(raw.get("canonical_sections", [])),
        aliases=aliases,
        sec_items=sec_items,
        transcript_markers=markers,
        confidence=dict(raw.get("confidence", {})),
        fallback_section=raw.get("fallback_section", "Uncategorized"),
        fallback_confidence=float(raw.get("fallback_confidence", 0.3)),
    )


@lru_cache
def get_taxonomy() -> Taxonomy:
    """Cached default taxonomy accessor."""
    return load_taxonomy()
