"""Unit tests for chunk validation rules."""

from __future__ import annotations

import pytest

from app.ingestion.chunking.chunk_validation import REQUIRED_METADATA_KEYS, ChunkValidator

VALID_META = {k: "x" for k in REQUIRED_METADATA_KEYS}


@pytest.mark.unit
def test_empty_chunk_is_fatal() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    res = v.validate(text="   ", token_count=0, metadata=VALID_META)
    assert not res.is_valid and "empty_chunk" in res.fatal


@pytest.mark.unit
def test_duplicate_chunk_is_fatal() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    first = v.validate(text="same content", token_count=100, metadata=VALID_META)
    second = v.validate(text="same content", token_count=100, metadata=VALID_META)
    assert first.is_valid
    assert not second.is_valid and "duplicate_chunk" in second.fatal


@pytest.mark.unit
def test_broken_metadata_is_fatal() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    res = v.validate(text="content", token_count=100, metadata={"company": "ACME"})
    assert not res.is_valid
    assert any(f.startswith("broken_metadata") for f in res.fatal)


@pytest.mark.unit
def test_too_small_is_warning_not_fatal() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    res = v.validate(text="tiny", token_count=3, metadata=VALID_META)
    assert res.is_valid
    assert any(w.startswith("too_small") for w in res.warnings)


@pytest.mark.unit
def test_too_large_is_warning_not_fatal() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    res = v.validate(text="big", token_count=5000, metadata=VALID_META)
    assert res.is_valid
    assert any(w.startswith("too_large") for w in res.warnings)


@pytest.mark.unit
def test_valid_chunk_has_no_issues() -> None:
    v = ChunkValidator(min_tokens=50, max_tokens=800)
    res = v.validate(text="a well sized chunk", token_count=400, metadata=VALID_META)
    assert res.is_valid and not res.warnings
