"""Canonical financial-metric taxonomy + value normalization (Phase 3A).

    from app.financial.metrics import (
        get_metric_taxonomy, MetricDefinition,
        resolve_alias, find_aliases_in_text,
        normalize_value, find_values, NormalizedValue,
    )
"""

from app.financial.metrics.metric_aliases import find_aliases_in_text, resolve_alias
from app.financial.metrics.normalization import (
    NormalizedValue,
    find_values,
    normalize_currency,
    normalize_value,
    parse_period,
)
from app.financial.metrics.taxonomy import (
    MetricDefinition,
    MetricTaxonomy,
    get_metric_taxonomy,
    load_metric_taxonomy,
)

__all__ = [
    "MetricTaxonomy",
    "MetricDefinition",
    "get_metric_taxonomy",
    "load_metric_taxonomy",
    "resolve_alias",
    "find_aliases_in_text",
    "NormalizedValue",
    "normalize_value",
    "find_values",
    "normalize_currency",
    "parse_period",
]
