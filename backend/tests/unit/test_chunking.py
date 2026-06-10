"""Unit tests for section-aware recursive chunking."""

from __future__ import annotations

import pytest

from app.ingestion.chunking.config import get_strategy
from app.ingestion.chunking.section_chunker import SectionChunker
from app.ingestion.chunking.token_counter import HeuristicTokenCounter

COUNTER = HeuristicTokenCounter()
CHUNKER = SectionChunker(COUNTER)


@pytest.mark.unit
def test_small_section_is_single_chunk() -> None:
    chunks = CHUNKER.chunk("A short risk factor statement.", get_strategy(None))
    assert chunks == ["A short risk factor statement."]


@pytest.mark.unit
def test_empty_section_yields_no_chunks() -> None:
    assert CHUNKER.chunk("   \n\n  ", get_strategy(None)) == []


@pytest.mark.unit
def test_long_section_splits_into_multiple_chunks_within_max() -> None:
    strategy = get_strategy(None)
    paragraphs = [f"paragraph{i} " + "word " * 100 for i in range(12)]
    text = "\n\n".join(paragraphs)

    chunks = CHUNKER.chunk(text, strategy)

    assert len(chunks) >= 2
    assert all(COUNTER.count(ch) <= strategy.max_tokens for ch in chunks)
    # Most chunks should be reasonably close to the target (not tiny).
    assert all(COUNTER.count(ch) > strategy.target_tokens // 3 for ch in chunks[:-1])


@pytest.mark.unit
def test_overlap_creates_shared_context() -> None:
    strategy = get_strategy(None)
    paragraphs = [f"P{i} " + "token " * 120 for i in range(8)]
    text = "\n\n".join(paragraphs)

    chunks = CHUNKER.chunk(text, strategy)
    total = sum(COUNTER.count(ch) for ch in chunks)
    original = COUNTER.count(text)
    # Overlap means the concatenated chunk tokens exceed the original.
    assert total > original


@pytest.mark.unit
def test_oversized_single_paragraph_is_hard_split() -> None:
    strategy = get_strategy(None)
    huge = "word " * 2000  # one paragraph, ~2000 tokens, no paragraph breaks
    chunks = CHUNKER.chunk(huge, strategy)
    assert len(chunks) >= 2
    assert all(COUNTER.count(ch) <= strategy.max_tokens for ch in chunks)


@pytest.mark.unit
def test_risk_factors_uses_smaller_target() -> None:
    # The Risk Factors strategy lowers the target so risks stay granular.
    assert get_strategy("Risk Factors").target_tokens < get_strategy(None).target_tokens


@pytest.mark.unit
def test_financial_statements_uses_table_separators() -> None:
    strat = get_strategy("Financial Statements")
    assert ". " not in strat.separators  # sentence splitting disabled for tables


@pytest.mark.unit
def test_chunking_is_deterministic() -> None:
    strategy = get_strategy(None)
    text = "\n\n".join(f"para{i} " + "word " * 90 for i in range(10))
    assert CHUNKER.chunk(text, strategy) == CHUNKER.chunk(text, strategy)
