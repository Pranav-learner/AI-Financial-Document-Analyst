"""Metric taxonomy loader (Phase 3A).

Loads the canonical financial-metric definitions (configurable JSON, override via
`METRIC_TAXONOMY_PATH`). Policy (which metrics, aliases, categories) lives in data,
not scattered through the code. Mirrors the Phase 1B section-taxonomy pattern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.config import settings

_DEFAULT_PATH = Path(__file__).with_name("taxonomy.json")


@dataclass(frozen=True)
class MetricDefinition:
    canonical: str                       # normalized_metric_name (e.g. REVENUE)
    category: str                        # MetricCategory value
    value_kind: str                      # "currency" | "percent"
    aliases: tuple[str, ...]             # lowercased surface forms
    expected_sections: tuple[str, ...]   # canonical section names (confidence boost)


@dataclass
class MetricTaxonomy:
    metrics: tuple[MetricDefinition, ...]
    # lowercased alias -> canonical, longest-alias-first for greedy matching
    alias_to_canonical: dict[str, str] = field(default_factory=dict)
    by_canonical: dict[str, MetricDefinition] = field(default_factory=dict)

    def canonicals(self) -> list[str]:
        return [m.canonical for m in self.metrics]

    def get(self, canonical: str) -> MetricDefinition | None:
        return self.by_canonical.get(canonical)

    def value_kind(self, canonical: str) -> str:
        d = self.by_canonical.get(canonical)
        return d.value_kind if d else "currency"


def _build(raw: dict) -> MetricTaxonomy:
    metrics: list[MetricDefinition] = []
    for m in raw.get("metrics", []):
        metrics.append(
            MetricDefinition(
                canonical=m["canonical"],
                category=m["category"],
                value_kind=m.get("value_kind", "currency"),
                aliases=tuple(a.lower() for a in m.get("aliases", [])),
                expected_sections=tuple(m.get("expected_sections", [])),
            )
        )
    alias_map: dict[str, str] = {}
    for d in metrics:
        for alias in d.aliases:
            alias_map.setdefault(alias, d.canonical)
    return MetricTaxonomy(
        metrics=tuple(metrics),
        alias_to_canonical=alias_map,
        by_canonical={d.canonical: d for d in metrics},
    )


def load_metric_taxonomy(path: str | Path | None = None) -> MetricTaxonomy:
    p = Path(path) if path else (
        Path(settings.metric_taxonomy_path) if settings.metric_taxonomy_path else _DEFAULT_PATH
    )
    raw = json.loads(p.read_text(encoding="utf-8"))
    return _build(raw)


@lru_cache
def get_metric_taxonomy() -> MetricTaxonomy:
    return load_metric_taxonomy()
