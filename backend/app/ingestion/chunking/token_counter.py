"""Configurable token counting (Phase 1C).

Token counting is abstracted behind a small protocol so a different tokenizer
(e.g. tiktoken or a model-specific tokenizer) can be swapped in later without
touching the chunker. Phase 1C ships deterministic, dependency-free counters.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.core.config import settings

# Word pieces + standalone punctuation — a deterministic approximation of
# subword token counts that needs no external tokenizer.
_TOKEN_RE = re.compile(r"\w+|[^\w\s]")


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class HeuristicTokenCounter:
    """Regex word/punctuation token estimate. Deterministic and fast."""

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(_TOKEN_RE.findall(text))


class CharTokenCounter:
    """~4 characters per token estimate (rough English heuristic)."""

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, round(len(text) / 4))


_REGISTRY: dict[str, TokenCounter] = {
    "heuristic": HeuristicTokenCounter(),
    "char": CharTokenCounter(),
}


def get_token_counter(name: str | None = None) -> TokenCounter:
    """Return the configured token counter (default from settings.tokenizer)."""
    key = (name or settings.tokenizer or "heuristic").lower()
    return _REGISTRY.get(key, _REGISTRY["heuristic"])
