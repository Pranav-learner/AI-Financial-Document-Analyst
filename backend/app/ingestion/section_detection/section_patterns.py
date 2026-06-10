"""Regex / heading heuristics for rule-based section detection (Phase 1B).

This module holds the *matching primitives* (regexes, line cleaning, heading
heuristics). The vocabulary (which headings map to which canonical section) lives
in the configurable taxonomy, not here — keeping policy (taxonomy) separate from
mechanism (patterns).
"""

from __future__ import annotations

import re
from collections.abc import Iterator

# A SEC item heading, e.g. "Item 1A.", "ITEM 7 -", "Item 8: Financial Statements".
SEC_ITEM_RE = re.compile(
    r"^\s*item\s+(\d{1,2}[A-Za-z]?)\b[\.\:\)\-\s]*(.*)$",
    re.IGNORECASE,
)

# "PART I", "PART II" — structural markers; not sections themselves, but they set
# the Part context used to disambiguate 10-Q item numbers.
PART_RE = re.compile(r"^\s*part\s+([ivx]+)\b", re.IGNORECASE)

# Table-of-contents style line: heading followed by dot leaders / a trailing page
# number (e.g. "Risk Factors .......... 23" or "Risk Factors      23"). These are
# pointers, not the section itself, so detection skips them to avoid false starts.
TOC_LINE_RE = re.compile(r"(\.{2,}\s*\d{1,4}|\s{2,}\d{1,4})\s*$")

# Leading enumeration to strip from a heading ("1A. ", "7) ", "I. ").
LEADING_ENUM_RE = re.compile(r"^\s*([0-9]{1,2}[A-Za-z]?|[IVXivx]+)[\.\)\:\-]\s+")

HEADING_MAX_LEN = 90
HEADING_MAX_WORDS = 14
_SENTENCE_END = (".", "!", "?", ";", ",")


def iter_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (char_offset, line) for each non-empty line in `text`."""
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            yield offset, stripped
        offset += len(line)


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def is_toc_line(line: str) -> bool:
    return bool(TOC_LINE_RE.search(line))


def clean_heading(line: str) -> str:
    """Strip TOC dot-leaders/page numbers and leading enumeration from a heading."""
    cleaned = TOC_LINE_RE.sub("", line)
    cleaned = LEADING_ENUM_RE.sub("", cleaned)
    cleaned = cleaned.strip(" \t-:.")
    return normalize_ws(cleaned)


def match_sec_item(line: str) -> tuple[str, str] | None:
    """Return (item_code, trailing_title) if the line is a SEC item heading."""
    m = SEC_ITEM_RE.match(line)
    if not m:
        return None
    return m.group(1).upper(), normalize_ws(m.group(2))


def is_strong_heading(line: str) -> bool:
    """Heuristic: a short, heading-like line (not a prose sentence)."""
    if not (2 <= len(line) <= HEADING_MAX_LEN):
        return False
    if len(line.split()) > HEADING_MAX_WORDS:
        return False
    # Headings rarely end in sentence punctuation (a trailing colon is fine).
    if line.endswith(_SENTENCE_END):
        return False
    return True


def is_mostly_uppercase(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    if not letters:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) >= 0.7
