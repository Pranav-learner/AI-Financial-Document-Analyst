"""Rule-based risk extraction (Phase 4).

Deterministic risk detection: scans document chunks for risk-indicating trigger
phrases and matches them against the taxonomy keywords to extract candidates.
Section-aware (Risk Factors section increases confidence). No LLM.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.risk.extraction.extraction_models import RiskCandidate, RiskChunkInput
from app.risk.extraction.severity_classifier import SeverityClassifier
from app.risk.taxonomy.normalization import normalize_category, normalize_risk_name, normalize_description
from app.risk.taxonomy.risk_categories import get_risk_taxonomy

log = get_logger(__name__)

# Core risk indicators to verify a block of text is actually discussing a risk.
_RISK_TRIGGERS = [
    re.compile(r"\brisk[s]?\b", re.IGNORECASE),
    re.compile(r"\buncertaint(y|ies)\b", re.IGNORECASE),
    re.compile(r"\badverse(ly)?\b", re.IGNORECASE),
    re.compile(r"\bthreat[s]?\b", re.IGNORECASE),
    re.compile(r"\bnegatively impact[s]?\b", re.IGNORECASE),
    re.compile(r"\bcould (impact|affect|harm|disrupt|damage|limit|prevent|reduce|impair)\b", re.IGNORECASE),
    re.compile(r"\bmay (impact|affect|harm|disrupt|damage|limit|prevent|reduce|impair)\b", re.IGNORECASE),
    re.compile(r"\bfail(ure|s)? to\b", re.IGNORECASE),
]


class RuleBasedRiskExtractor:
    def __init__(self, window: int = 200) -> None:
        self.taxonomy = get_risk_taxonomy()
        self.severity_classifier = SeverityClassifier()
        self.window = window

    def extract(self, chunks: list[RiskChunkInput]) -> list[RiskCandidate]:
        candidates: list[RiskCandidate] = []
        for ch in chunks:
            candidates.extend(self._extract_chunk(ch))
        return self._dedupe(candidates)

    def _extract_chunk(self, ch: RiskChunkInput) -> list[RiskCandidate]:
        candidates: list[RiskCandidate] = []
        
        # Check if the chunk contains any risk indicators first
        has_trigger = any(trigger.search(ch.text) for trigger in _RISK_TRIGGERS)
        if not has_trigger:
            return []

        # Section match: Check if chunk belongs to standard risk disclosure sections
        is_risk_section = False
        norm_sec = (ch.normalized_section_name or "").upper()
        if norm_sec in ("RISK FACTORS", "MD&A", "FORWARD GUIDANCE", "FORWARD-LOOKING STATEMENTS"):
            is_risk_section = True

        # Split text into sentences for fine-grained keyword matching
        sentences = [s.strip() for s in re.split(r'(?<=[.!?]) +', ch.text) if s.strip()]

        for sent in sentences:
            # Check if this sentence contains a risk trigger
            if not any(trigger.search(sent) for trigger in _RISK_TRIGGERS):
                continue

            # Check taxonomy keyword matches in the sentence
            matches = self.taxonomy.classify_by_keywords_all(sent)
            for cat_name in matches:
                cat_def = self.taxonomy.get(cat_name)
                if not cat_def:
                    continue

                # Find the specific keyword that matched
                matched_kw = None
                for kw in cat_def.keywords:
                    if kw.lower() in sent.lower():
                        matched_kw = kw
                        break
                
                if not matched_kw:
                    continue

                # Derive a friendly risk name from the matched keyword
                # e.g., "supply chain" -> "Supply Chain Risk"
                risk_name = f"{matched_kw.title()} Risk"
                norm_name = normalize_risk_name(risk_name)

                # Description: take the surrounding context of the sentence (the sentence itself)
                desc = normalize_description(sent)
                severity = self.severity_classifier.classify(desc)
                
                # Confidence base
                confidence = 0.75
                if is_risk_section:
                    confidence += 0.05

                candidates.append(
                    RiskCandidate(
                        risk_name=risk_name,
                        normalized_risk_name=norm_name,
                        risk_description=desc,
                        category=cat_name,
                        severity=severity,
                        source_chunk_id=ch.chunk_id,
                        source_text=sent,
                        method="RULE_BASED",
                        raw_confidence=min(0.85, confidence),
                        section_match=is_risk_section,
                        extraction_metadata={
                            "matched_keyword": matched_kw,
                            "sentence_matched": sent,
                        }
                    )
                )

        return candidates

    @staticmethod
    def _dedupe(candidates: list[RiskCandidate]) -> list[RiskCandidate]:
        """Keep the highest-confidence candidate per normalized risk name."""
        best: dict[str, RiskCandidate] = {}
        for c in candidates:
            cur = best.get(c.key())
            if cur is None or c.raw_confidence > cur.raw_confidence:
                best[c.key()] = c
        return list(best.values())
