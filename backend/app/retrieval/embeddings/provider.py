"""Embedding provider abstraction (Phase 2A).

Defines the stable interface that the embedding service depends on, so the
concrete model (Gemini today) can be swapped without touching business logic
(ADR-003 / ADR-013). A provider's job is narrow: turn texts into vectors,
reliably (retries, rate-limit handling, response validation, normalization).

Design note — task types: documents (stored chunks) are embedded with the
`RETRIEVAL_DOCUMENT` task type (Phase 2A). The **query** path (`embed_query`,
`RETRIEVAL_QUERY`) is added in Phase 2B for search — Gemini produces asymmetric
embeddings tuned for document-vs-query, so the query side must use its own task
type for good retrieval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

# A single embedding is a list of floats; a batch is a list of those.
Embedding = list[float]


class EmbeddingProvider(ABC):
    """Abstract embedding generator.

    Implementations MUST guarantee that `embed_documents` returns exactly one
    vector per input text, in order, each of width `dimension`, or raise an
    `EmbeddingError`. Empty input returns an empty list (no provider call).
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the underlying model (stored on each chunk for re-embeds)."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Width of every produced vector. Must match the DB column."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        """Embed document chunks for storage (RETRIEVAL_DOCUMENT task type).

        Returns one vector per input text, in the same order. Handles retries,
        rate limits, response validation, and (if configured) normalization
        internally. Raises `EmbeddingError` on permanent failure.
        """

    def embed_query(self, text: str) -> Embedding:
        """Embed a search query (Phase 2B), returning a single vector.

        Default delegates to `embed_documents` so simple/test providers work
        unchanged; the Gemini provider overrides this to use the `RETRIEVAL_QUERY`
        task type for asymmetric document-vs-query retrieval. Same width/retry/
        validation/normalization guarantees as `embed_documents`.
        """
        return self.embed_documents([text])[0]
