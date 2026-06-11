"""Ground-truth dataset for retrieval evaluation (Phase 2D).

Loads a reusable benchmark suite (default: packaged `benchmark_suite.json`,
override via `RETRIEVAL_BENCHMARK_PATH`) and judges whether a retrieved result is
relevant to an example. Relevance is corpus-portable: it matches on canonical
`normalized_section_name` (and optionally curated report/chunk ids), so the same
suite works against any ingested corpus without hardcoding chunk ids in tests.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.retrieval.evaluation.evaluation_exceptions import GroundTruthError
from app.retrieval.search.retrieval_models import SearchResult

_DEFAULT_PATH = Path(__file__).with_name("benchmark_suite.json")


@dataclass
class GroundTruthExample:
    id: str
    query: str
    category: str
    expected_sections: tuple[str, ...] = ()
    expected_report_ids: tuple[str, ...] = ()
    expected_chunk_ids: tuple[str, ...] = ()
    profile: str | None = None
    filters: dict = field(default_factory=dict)

    def is_relevant(self, result: SearchResult) -> bool:
        """Authoritative relevance: chunk ids if curated, else section, else report."""
        if self.expected_chunk_ids:
            return str(result.chunk_id) in self.expected_chunk_ids
        if self.expected_sections:
            name = (result.metadata or {}).get("normalized_section_name")
            return name in self.expected_sections
        if self.expected_report_ids:
            return str(result.report_id) in self.expected_report_ids
        return False


def _parse(raw: dict) -> list[GroundTruthExample]:
    examples = raw.get("examples")
    if not isinstance(examples, list) or not examples:
        raise GroundTruthError("benchmark suite has no examples")
    out: list[GroundTruthExample] = []
    for e in examples:
        try:
            out.append(
                GroundTruthExample(
                    id=e["id"],
                    query=e["query"],
                    category=e.get("category", "GENERAL"),
                    expected_sections=tuple(e.get("expected_sections", ())),
                    expected_report_ids=tuple(e.get("expected_report_ids", ())),
                    expected_chunk_ids=tuple(e.get("expected_chunk_ids", ())),
                    profile=e.get("profile"),
                    filters=e.get("filters", {}) or {},
                )
            )
        except KeyError as exc:
            raise GroundTruthError(f"benchmark example missing field: {exc}") from exc
    return out


def load_ground_truth(path: str | Path | None = None) -> list[GroundTruthExample]:
    p = Path(path) if path else (
        Path(settings.retrieval_benchmark_path)
        if settings.retrieval_benchmark_path
        else _DEFAULT_PATH
    )
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GroundTruthError(f"benchmark suite not found: {p}") from exc
    except json.JSONDecodeError as exc:
        raise GroundTruthError(f"benchmark suite is not valid JSON: {exc}") from exc
    return _parse(raw)


@lru_cache
def get_ground_truth() -> list[GroundTruthExample]:
    """Cached default suite (most callers want this)."""
    return load_ground_truth()


def normalize_uuid(value: str) -> uuid.UUID:
    return uuid.UUID(value)
