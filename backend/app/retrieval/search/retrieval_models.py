"""Retrieval data contracts (Phase 2B).

`SearchResult` is the standard retrieval unit that future phases (re-ranking,
hybrid retrieval, RAG, agents) build on — keep it stable. These are plain
dataclasses (transport-agnostic); the API layer maps them to Pydantic schemas.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """One retrieved chunk + its similarity score. The retrieval contract."""

    chunk_id: uuid.UUID
    report_id: uuid.UUID
    section_id: uuid.UUID | None
    score: float                 # cosine similarity in [-1, 1] (≈[0,1] in practice)
    chunk_text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryEmbeddingStats:
    """Diagnostics about the query vector (debug endpoint / observability)."""

    dimension: int
    norm: float
    preview: list[float]         # first few components, for eyeballing
    model: str
    task_type: str


@dataclass
class SearchTimings:
    """Latency breakdown in milliseconds (task §10 observability)."""

    embedding_ms: float = 0.0
    vector_search_ms: float = 0.0
    total_ms: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass
class SearchOutcome:
    """Internal result of a search run: results + timings + counts."""

    results: list[SearchResult]
    timings: SearchTimings
    requested_top_k: int
    returned: int
