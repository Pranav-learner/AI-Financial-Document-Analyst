"""HyDE service orchestration (Phase 6)."""

from __future__ import annotations

from app.core.logging import get_logger
from app.rag.hyde.hyde_generator import HyDEGenerator
from app.rag.hyde.models import HyDEResult
from app.retrieval.search.query_embedding import QueryEmbedder
from app.retrieval.embeddings.provider import Embedding
from app.retrieval.search.retrieval_models import QueryEmbeddingStats

log = get_logger(__name__)


class HyDEService:
    """Orchestrates HyDE generation and produces hypothetical document embeddings."""

    def __init__(
        self,
        query_embedder: QueryEmbedder,
        *,
        generator: HyDEGenerator | None = None
    ) -> None:
        self.query_embedder = query_embedder
        self.generator = generator or HyDEGenerator()

    def generate_hyde_embedding(self, query: str) -> tuple[Embedding, QueryEmbeddingStats, HyDEResult]:
        # 1. Generate hypothetical answer text
        res = self.generator.generate(query)

        # 2. Embed hypothetical text
        log.info("hyde.embedding_generation", query=query, doc_preview=res.hypothetical_document[:60])
        vector, stats = self.query_embedder.embed(res.hypothetical_document)

        return vector, stats, res
