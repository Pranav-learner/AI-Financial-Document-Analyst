"""Phase 2B — HNSW ANN index on document_chunks.embedding (cosine)

Revision ID: 0005_phase2b
Revises: 0004_phase2a
Create Date: 2026-06-11

Adds the approximate-nearest-neighbour index that makes vector similarity search
fast at scale. This is the index deliberately deferred from Phase 2A.

Distance metric: **cosine** (`vector_cosine_ops`). Embeddings are unit-normalized
(Phase 2A re-normalizes the truncated 768-dim Gemini vectors), so cosine distance
is the natural, well-conditioned metric; similarity score = 1 - cosine_distance.
(See ADR-014.)

HNSW chosen over IVFFlat: better recall/latency tradeoff, no training step, and
robust as rows are added incrementally. Build parameters: m=16, ef_construction=64
(pgvector defaults — good general-purpose recall/build-time balance). Query-time
recall is tuned with `hnsw.ef_search` (GUC), not baked into the index.

Production note: this issues a plain CREATE INDEX (write-locking) because Alembic
wraps migrations in a transaction and `CREATE INDEX CONCURRENTLY` cannot run
inside one. For a large pre-populated table, build the index out-of-band with
CONCURRENTLY instead. Reversible: downgrade drops the index only.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_phase2b"
down_revision: str | None = "0004_phase2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "ix_document_chunks_embedding_hnsw"
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 64


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
        f"ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        f"WITH (m = {HNSW_M}, ef_construction = {HNSW_EF_CONSTRUCTION})"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
