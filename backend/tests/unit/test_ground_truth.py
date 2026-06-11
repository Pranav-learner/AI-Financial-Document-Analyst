"""Unit tests for ground-truth dataset + relevance judgment (Phase 2D)."""

from __future__ import annotations

import json
import uuid

import pytest
from app.retrieval.evaluation.evaluation_exceptions import GroundTruthError
from app.retrieval.evaluation.ground_truth import (
    GroundTruthExample,
    get_ground_truth,
    load_ground_truth,
)
from app.retrieval.search.retrieval_models import SearchResult


def _result(section=None, report_id=None, chunk_id=None) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        report_id=report_id or uuid.uuid4(),
        section_id=None,
        score=0.9,
        chunk_text="x",
        metadata={"normalized_section_name": section} if section else {},
    )


@pytest.mark.unit
def test_packaged_suite_loads() -> None:
    examples = get_ground_truth()
    assert len(examples) >= 5
    assert {"RISK", "FINANCIAL_STATEMENTS", "GUIDANCE"} <= {e.category for e in examples}


@pytest.mark.unit
def test_relevance_by_section() -> None:
    ex = GroundTruthExample(id="x", query="q", category="RISK", expected_sections=("Risk Factors",))
    assert ex.is_relevant(_result(section="Risk Factors")) is True
    assert ex.is_relevant(_result(section="MD&A")) is False


@pytest.mark.unit
def test_relevance_by_chunk_id_takes_priority() -> None:
    cid = uuid.uuid4()
    ex = GroundTruthExample(
        id="x", query="q", category="RISK",
        expected_sections=("MD&A",),                 # would say "not relevant"...
        expected_chunk_ids=(str(cid),),              # ...but chunk id wins
    )
    assert ex.is_relevant(_result(section="MD&A", chunk_id=cid)) is True
    assert ex.is_relevant(_result(section="MD&A")) is False  # different chunk


@pytest.mark.unit
def test_relevance_by_report_id() -> None:
    rid = uuid.uuid4()
    ex = GroundTruthExample(id="x", query="q", category="GENERAL", expected_report_ids=(str(rid),))
    assert ex.is_relevant(_result(report_id=rid)) is True
    assert ex.is_relevant(_result()) is False


@pytest.mark.unit
def test_missing_file_raises(tmp_path) -> None:
    with pytest.raises(GroundTruthError):
        load_ground_truth(tmp_path / "nope.json")


@pytest.mark.unit
def test_empty_suite_raises(tmp_path) -> None:
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"examples": []}))
    with pytest.raises(GroundTruthError):
        load_ground_truth(p)
