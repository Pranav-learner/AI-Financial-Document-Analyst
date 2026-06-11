"""Unit tests for confidence scoring (Phase 3A)."""

from __future__ import annotations

import pytest
from app.financial.extraction.confidence_scoring import compute_confidence


@pytest.mark.unit
def test_agreement_is_highest() -> None:
    c = compute_confidence("HYBRID_VALIDATED", section_match=True, has_currency_or_scale=True)
    assert c >= 0.95


@pytest.mark.unit
def test_rule_with_evidence() -> None:
    c = compute_confidence("RULE_BASED", section_match=True, has_currency_or_scale=True)
    assert 0.85 <= c <= 0.95


@pytest.mark.unit
def test_rule_weak_evidence() -> None:
    c = compute_confidence("RULE_BASED", section_match=False, has_currency_or_scale=False)
    assert c == 0.60


@pytest.mark.unit
def test_llm_only_around_0_70() -> None:
    c = compute_confidence("LLM_BASED", llm_confidence=0.8)
    assert 0.65 <= c <= 0.75


@pytest.mark.unit
def test_disagreement_is_low() -> None:
    c = compute_confidence("RULE_BASED", disagreement=True)
    assert c == 0.45


@pytest.mark.unit
def test_ordering_agreement_gt_rule_gt_llm() -> None:
    agree = compute_confidence("HYBRID_VALIDATED", section_match=True, has_currency_or_scale=True)
    rule = compute_confidence("RULE_BASED", section_match=True, has_currency_or_scale=True)
    llm = compute_confidence("LLM_BASED", llm_confidence=0.7)
    assert agree > rule > llm
