"""Unit tests for configurable token counting."""

from __future__ import annotations

import pytest

from app.ingestion.chunking.token_counter import (
    CharTokenCounter,
    HeuristicTokenCounter,
    get_token_counter,
)


@pytest.mark.unit
def test_heuristic_counts_words_and_punctuation() -> None:
    c = HeuristicTokenCounter()
    assert c.count("Hello, world") == 3       # Hello , world
    assert c.count("") == 0
    assert c.count("revenue increased 10%") == 4  # revenue increased 10 %


@pytest.mark.unit
def test_heuristic_is_deterministic() -> None:
    c = HeuristicTokenCounter()
    text = "The quick brown fox jumps over the lazy dog."
    assert c.count(text) == c.count(text)


@pytest.mark.unit
def test_char_counter() -> None:
    c = CharTokenCounter()
    assert c.count("") == 0
    assert c.count("abcd") == 1
    assert c.count("a" * 40) == 10


@pytest.mark.unit
def test_registry_factory_defaults_to_heuristic() -> None:
    assert isinstance(get_token_counter("heuristic"), HeuristicTokenCounter)
    assert isinstance(get_token_counter("char"), CharTokenCounter)
    assert isinstance(get_token_counter("unknown"), HeuristicTokenCounter)
