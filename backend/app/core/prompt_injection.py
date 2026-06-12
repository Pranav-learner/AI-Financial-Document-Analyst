"""Prompt Injection Guard (Phase 11)."""

from __future__ import annotations

import re
from app.core.exceptions import ValidationError

# Heuristic patterns for detecting common prompt injection attempts
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
    r"(?i)system\s+override",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)act\s+as\s+a",
    r"(?i)developer\s+mode",
    r"(?i)bypass\s+safety",
    r"(?i)forget\s+(?:all\s+)?instructions",
    r"(?i)new\s+rule\s+supersedes",
]

_COMPILED_PATTERNS = [re.compile(p) for p in PROMPT_INJECTION_PATTERNS]


def guard_prompt(text: str | None) -> None:
    """Scan a string input for prompt injection signatures.
    
    Raises ValidationError if any match is found.
    """
    if not text:
        return

    # Check for compiled regex matches
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            raise ValidationError(
                "Input rejected due to detected prompt injection signature.",
                details={"malicious_pattern_match": pattern.pattern}
            )
