"""Section-aware recursive chunking (Phase 1C).

Deterministic, LLM-free preparation of retrieval-ready knowledge chunks from
`report_sections`. No embeddings or vector storage (Phase 2). Public surface:

    from app.ingestion.chunking import ChunkGenerator, SectionInput, GeneratedChunk
    from app.ingestion.chunking.metadata_builder import ReportContext
"""

from app.ingestion.chunking.chunker import (
    ChunkGenerator,
    GeneratedChunk,
    SectionInput,
)
from app.ingestion.chunking.metadata_builder import ReportContext

__all__ = ["ChunkGenerator", "SectionInput", "GeneratedChunk", "ReportContext"]
