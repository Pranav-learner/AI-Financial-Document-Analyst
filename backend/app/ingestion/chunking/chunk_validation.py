"""Chunk validation (Phase 1C).

Validates candidate chunks before persistence. Distinguishes:
  * FATAL issues (empty, duplicate, broken metadata) → chunk is dropped, logged.
  * WARNING issues (too small / too large) → chunk is kept but logged for quality review.

Duplicate detection is content-hash based and scoped to a single report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

REQUIRED_METADATA_KEYS = {
    "company",
    "report_type",
    "year",
    "quarter",
    "section_name",
    "normalized_section_name",
    "start_page",
    "end_page",
    "report_id",
    "section_id",
}


@dataclass
class ValidationResult:
    fatal: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.fatal


class ChunkValidator:
    """Stateful validator (tracks seen content hashes for duplicate detection)."""

    def __init__(self, min_tokens: int, max_tokens: int) -> None:
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self._seen_hashes: set[str] = set()

    @staticmethod
    def content_hash(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def validate(self, *, text: str, token_count: int, metadata: dict) -> ValidationResult:
        result = ValidationResult()

        if not text or not text.strip():
            result.fatal.append("empty_chunk")
            return result  # nothing else matters

        digest = self.content_hash(text)
        if digest in self._seen_hashes:
            result.fatal.append("duplicate_chunk")
        else:
            self._seen_hashes.add(digest)

        missing = REQUIRED_METADATA_KEYS - set(metadata.keys())
        if missing:
            result.fatal.append(f"broken_metadata: missing {sorted(missing)}")

        if token_count < self.min_tokens:
            result.warnings.append(f"too_small: {token_count} < {self.min_tokens}")
        if token_count > self.max_tokens:
            result.warnings.append(f"too_large: {token_count} > {self.max_tokens}")

        return result
