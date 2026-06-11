"""Vector similarity search over pgvector (Phase 2B, task §2/§4).

Pure ANN retrieval: given a query vector, return the top-K nearest chunks by
**cosine distance**, newest HNSW index. NO metadata filtering, NO re-ranking,
NO post-processing — those belong to later phases. The only predicate is
`embedding IS NOT NULL` (a not-yet-embedded chunk has nothing to compare), which
is data integrity, not metadata filtering.

Score = 1 - cosine_distance, i.e. cosine similarity in [-1, 1] (≈[0, 1] for
these unit-normalized embeddings): 1.0 identical, ~0 unrelated.
"""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document_chunk import DocumentChunk
from app.retrieval.embeddings.provider import Embedding
from app.retrieval.search.retrieval_models import SearchResult

log = get_logger(__name__)


class VectorSearch:
    """Executes the cosine KNN query against `document_chunks`."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(self, query_vector: Embedding, *, top_k: int) -> list[SearchResult]:
        # Tune HNSW query-time recall for this transaction (GUC; int from config).
        await self.session.execute(
            text(f"SET LOCAL hnsw.ef_search = {int(settings.hnsw_ef_search)}")
        )

        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        stmt = (
            select(DocumentChunk, distance)
            .where(DocumentChunk.embedding.is_not(None))
            .order_by(distance)
            .limit(top_k)
        )
        rows = (await self.session.execute(stmt)).all()

        results = [
            SearchResult(
                chunk_id=chunk.id,
                report_id=chunk.report_id,
                section_id=chunk.section_id,
                score=round(1.0 - float(dist), 6),
                chunk_text=chunk.chunk_text,
                metadata=chunk.chunk_metadata or {},
            )
            for chunk, dist in rows
        ]
        log.info("search.vector_query", top_k=top_k, returned=len(results))
        return results
