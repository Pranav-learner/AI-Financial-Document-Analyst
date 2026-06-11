"""Deterministic severity classifier (Phase 4).

Classifies risk severity based on keyword indicators in the risk description.
Thresholds and keyword lists are configurable. Deterministic — no LLM involvement.

Severity levels:
  * CRITICAL: existential threat, substantial impairment, severe regulatory action.
  * HIGH: significant disruption, material adverse effect, major impact.
  * MEDIUM: may impact operations, moderate dependence, could affect.
  * LOW: minor exposure, limited impact, unlikely.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger

log = get_logger(__name__)

# Keywords sorted roughly by severity — checked top-down, first match wins.
_CRITICAL_KEYWORDS = [
    "existential threat", "substantial impairment", "severe regulatory action",
    "going concern", "bankruptcy", "insolvency", "cessation of operations",
    "catastrophic", "irreparable", "criminal", "severe adverse",
    "total loss", "complete failure", "systemic risk",
]

_HIGH_KEYWORDS = [
    "material adverse effect", "material adverse impact", "materially affect",
    "materially impact", "significant disruption", "significant adverse",
    "could materially", "may materially", "material risk",
    "substantial risk", "serious risk", "major impact",
    "significant harm", "significant loss", "critical vulnerability",
    "adversely affect our business", "adversely impact",
]

_MEDIUM_KEYWORDS = [
    "may impact", "could impact", "may affect", "could affect",
    "moderate", "could negatively impact", "may adversely",
    "could adversely", "potential impact", "may result in",
    "could result in", "uncertainty", "exposure to",
    "dependence on", "subject to", "vulnerable", "vulnerability",
    "disruption", "adverse effect",
]

_LOW_KEYWORDS = [
    "minor", "limited impact", "limited exposure", "unlikely",
    "not expected to be material", "immaterial", "de minimis",
    "low probability", "remote", "insignificant",
]

# Compile all patterns for efficient matching.
_SEVERITY_LEVELS = [
    ("CRITICAL", _CRITICAL_KEYWORDS),
    ("HIGH", _HIGH_KEYWORDS),
    ("MEDIUM", _MEDIUM_KEYWORDS),
    ("LOW", _LOW_KEYWORDS),
]

_COMPILED: list[tuple[str, list[re.Pattern]]] = [
    (severity, [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords])
    for severity, keywords in _SEVERITY_LEVELS
]


class SeverityClassifier:
    """Deterministic severity scoring for extracted risks."""

    def classify(self, description: str) -> str:
        """Return the severity level for a risk description.

        Scans for keyword indicators from CRITICAL → LOW. First match wins.
        If no keywords match, defaults to MEDIUM.
        """
        for severity, patterns in _COMPILED:
            for pattern in patterns:
                if pattern.search(description):
                    return severity
        return "MEDIUM"

    def classify_with_evidence(self, description: str) -> tuple[str, str | None]:
        """Return (severity, matched_keyword) for observability."""
        for severity, keywords in _SEVERITY_LEVELS:
            for kw in keywords:
                if kw.lower() in description.lower():
                    return severity, kw
        return "MEDIUM", None
