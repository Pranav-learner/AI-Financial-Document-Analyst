"""RiskMatcher (Phase 4).

Matches risks across reporting periods to establish continuity.
Uses a hybrid matching strategy:
  1. Exact match on normalized_risk_name.
  2. Fuzzy match on token overlap similarity, restricted to the same category.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.risk.evolution.models import RiskMatch

if TYPE_CHECKING:
    from app.models.risk_factor import RiskFactor

_STOP_WORDS = {
    "risk", "factors", "and", "or", "the", "a", "of", "to", "in", "for",
    "on", "with", "at", "by", "from", "up", "about", "into", "over", "after",
}

_WORD = re.compile(r"\w+")


def _get_tokens(name: str) -> set[str]:
    """Tokenize and remove stop words."""
    words = _WORD.findall(name.lower())
    return {w for w in words if w not in _STOP_WORDS}


def calculate_jaccard(name1: str, name2: str) -> float:
    tokens1 = _get_tokens(name1)
    tokens2 = _get_tokens(name2)
    if not tokens1 or not tokens2:
        return 0.0
    union = tokens1.union(tokens2)
    intersection = tokens1.intersection(tokens2)
    return len(intersection) / len(union)


class RiskMatcher:
    def __init__(self, fuzzy_threshold: float = 0.4) -> None:
        self.fuzzy_threshold = fuzzy_threshold

    def match_risks(
        self,
        current_risks: list[RiskFactor],
        previous_risks: list[RiskFactor],
    ) -> list[RiskMatch]:
        """Match current period risks to previous period risks.

        Returns a list of RiskMatch objects mapping pairs of matched risks,
        or unmatched current/previous risks.
        """
        matched_current: set[str] = set()  # set of current_risk.id (as string)
        matched_previous: set[str] = set()  # set of previous_risk.id (as string)
        matches: list[RiskMatch] = []

        # Convert IDs to string just in case
        curr_map = {str(r.id): r for r in current_risks}
        prev_map = {str(r.id): r for r in previous_risks}

        # 1. Exact Match on normalized_risk_name
        for cid, curr in curr_map.items():
            for pid, prev in prev_map.items():
                if pid in matched_previous:
                    continue
                if curr.normalized_risk_name == prev.normalized_risk_name:
                    matches.append(
                        RiskMatch(
                            current_id=cid,
                            previous_id=pid,
                            current_name=curr.risk_name,
                            previous_name=prev.risk_name,
                            category=curr.category,
                            match_type="EXACT",
                            match_score=1.0,
                        )
                    )
                    matched_current.add(cid)
                    matched_previous.add(pid)
                    break

        # 2. Fuzzy Match on token overlap (restricted to the same category)
        for cid, curr in curr_map.items():
            if cid in matched_current:
                continue
            
            best_pid = None
            best_score = 0.0

            for pid, prev in prev_map.items():
                if pid in matched_previous:
                    continue
                if curr.category != prev.category:
                    continue

                score = calculate_jaccard(curr.risk_name, prev.risk_name)
                if score >= self.fuzzy_threshold and score > best_score:
                    best_score = score
                    best_pid = pid

            if best_pid:
                matches.append(
                    RiskMatch(
                        current_id=cid,
                        previous_id=best_pid,
                        current_name=curr.risk_name,
                        previous_name=prev_map[best_pid].risk_name,
                        category=curr.category,
                        match_type="FUZZY",
                        match_score=round(best_score, 3),
                    )
                )
                matched_current.add(cid)
                matched_previous.add(best_pid)

        # 3. Unmatched Current Risks (NEW_RISK)
        for cid, curr in curr_map.items():
            if cid not in matched_current:
                matches.append(
                    RiskMatch(
                        current_id=cid,
                        previous_id=None,
                        current_name=curr.risk_name,
                        previous_name=None,
                        category=curr.category,
                        match_type="NONE",
                        match_score=0.0,
                    )
                )

        # 4. Unmatched Previous Risks (REMOVED_RISK)
        for pid, prev in prev_map.items():
            if pid not in matched_previous:
                matches.append(
                    RiskMatch(
                        current_id=None,
                        previous_id=pid,
                        current_name=None,
                        previous_name=prev.risk_name,
                        category=prev.category,
                        match_type="NONE",
                        match_score=0.0,
                    )
                )

        return matches
