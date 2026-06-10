"""Chunk generation orchestrator (Phase 1C).

Ties together section-aware recursive splitting, metadata building, token counting,
and validation to turn a report's sections into an ordered, validated list of
chunks. Deterministic and repeatable: same input → same chunks, same order.

Page attribution: Phase 1A stores page text concatenated per section without
per-page offsets, so each chunk inherits its section's page span (start_page/
end_page). Finer per-chunk page mapping is a documented future improvement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.ingestion.chunking.chunk_validation import ChunkValidator
from app.ingestion.chunking.config import get_strategy
from app.ingestion.chunking.metadata_builder import (
    ReportContext,
    SectionContext,
    build_metadata,
)
from app.ingestion.chunking.section_chunker import SectionChunker
from app.ingestion.chunking.token_counter import TokenCounter, get_token_counter

log = get_logger(__name__)


@dataclass(frozen=True)
class SectionInput:
    section_id: str
    section_name: str
    normalized_section_name: str
    start_page: int
    end_page: int
    content: str


@dataclass(frozen=True)
class GeneratedChunk:
    chunk_index: int
    chunk_text: str
    token_count: int
    start_page: int
    end_page: int
    section_id: str | None
    metadata: dict[str, Any]


class ChunkGenerator:
    def __init__(self, counter: TokenCounter | None = None) -> None:
        self.counter = counter or get_token_counter()
        self.section_chunker = SectionChunker(self.counter)

    def generate(
        self, report: ReportContext, sections: list[SectionInput]
    ) -> list[GeneratedChunk]:
        validator = ChunkValidator(
            min_tokens=settings.chunk_min_tokens, max_tokens=settings.chunk_max_tokens
        )
        chunks: list[GeneratedChunk] = []
        dropped = 0
        index = 0

        for section in sections:
            strategy = get_strategy(section.normalized_section_name)
            pieces = self.section_chunker.chunk(section.content, strategy)
            sec_ctx = SectionContext(
                section_id=section.section_id,
                section_name=section.section_name,
                normalized_section_name=section.normalized_section_name,
                start_page=section.start_page,
                end_page=section.end_page,
            )
            for piece in pieces:
                token_count = self.counter.count(piece)
                metadata = build_metadata(report, sec_ctx)
                result = validator.validate(
                    text=piece, token_count=token_count, metadata=metadata
                )
                if not result.is_valid:
                    dropped += 1
                    log.warning(
                        "chunk.dropped",
                        section=section.normalized_section_name,
                        issues=result.fatal,
                    )
                    continue
                if result.warnings:
                    log.info(
                        "chunk.warning",
                        section=section.normalized_section_name,
                        warnings=result.warnings,
                    )
                chunks.append(
                    GeneratedChunk(
                        chunk_index=index,
                        chunk_text=piece,
                        token_count=token_count,
                        start_page=section.start_page,
                        end_page=section.end_page,
                        section_id=section.section_id,
                        metadata=metadata,
                    )
                )
                index += 1

        log.info("chunks.generated", count=len(chunks), dropped=dropped)
        return chunks
