"""Unit tests for the LLM metric extractor (Phase 3A) — no network/SDK."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from app.financial.extraction.exceptions import LLMTransientError
from app.financial.extraction.extraction_models import ChunkInput
from app.financial.extraction.llm_extractor import LLMExtractor


def _chunk(text="Total revenue was $96.7 billion.", section="Income Statement"):
    return ChunkInput(chunk_id="c1", text=text, normalized_section_name=section,
                      fiscal_year=2024, fiscal_quarter=None)


def _llm(json_text, *, errors=None, api_key="x"):
    seq = list(errors or [])

    class _Fake(LLMExtractor):
        def _generate(self, text):
            if seq:
                raise seq.pop(0)
            return json_text

    return _Fake(api_key=api_key, model="gemini-2.5-pro", base_delay=0.0,
                 client=object(), sleep=lambda _d: None)


@pytest.mark.unit
def test_disabled_without_key_returns_empty() -> None:
    llm = LLMExtractor(api_key="", model="x")
    assert llm.enabled is False
    assert llm.extract([_chunk()]) == []


@pytest.mark.unit
def test_parses_and_normalizes() -> None:
    payload = json.dumps([
        {"metric_name": "Total Revenue", "value": 96.7, "unit": "billion", "currency": "USD",
         "period": "fiscal 2024", "confidence": 0.9},
    ])
    out = _llm(payload).extract([_chunk()])
    assert len(out) == 1
    c = out[0]
    assert c.normalized_metric_name == "REVENUE"
    assert c.value == Decimal("96700000000.0")
    assert c.unit == "BILLION" and c.currency == "USD"
    assert c.method == "LLM_BASED" and c.source_chunk_id == "c1"


@pytest.mark.unit
def test_percent_metric() -> None:
    payload = json.dumps([{"metric_name": "operating margin", "value": 28.5, "unit": "percent"}])
    out = _llm(payload).extract([_chunk(section="MD&A")])
    assert out[0].normalized_metric_name == "OPERATING_MARGIN"
    assert out[0].value == Decimal("28.5") and out[0].unit == "PERCENT"


@pytest.mark.unit
def test_unknown_metric_name_skipped() -> None:
    payload = json.dumps([{"metric_name": "Quantum Ratio", "value": 5, "unit": "billion"}])
    assert _llm(payload).extract([_chunk()]) == []


@pytest.mark.unit
def test_malformed_json_degrades_to_empty() -> None:
    # extract() catches per-chunk LLM failures and returns what it can ([] here)
    assert _llm("{not json").extract([_chunk()]) == []


@pytest.mark.unit
def test_retries_transient_then_succeeds() -> None:
    payload = json.dumps([{"metric_name": "Revenue", "value": 96.7, "unit": "billion"}])
    out = _llm(payload, errors=[LLMTransientError("429")]).extract([_chunk()])
    assert len(out) == 1 and out[0].normalized_metric_name == "REVENUE"
