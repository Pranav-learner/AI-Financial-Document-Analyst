"""Chunk lookup endpoint (Phase 1C). Mounted at /api/v1/chunks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.repositories.report_repository import ReportRepository
from app.schemas.report import ChunkOut

router = APIRouter()


@router.get("/{chunk_id}", response_model=ChunkOut, summary="Get one chunk (with text + metadata)")
async def get_chunk(
    chunk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ChunkOut:
    repo = ReportRepository(db)
    chunk = await repo.get_chunk(chunk_id)
    if chunk is None:
        raise NotFoundError("Chunk not found", details={"chunk_id": str(chunk_id)})
    return ChunkOut(
        id=chunk.id,
        report_id=chunk.report_id,
        section_id=chunk.section_id,
        chunk_index=chunk.chunk_index,
        chunk_text=chunk.chunk_text,
        token_count=chunk.token_count,
        start_page=chunk.start_page,
        end_page=chunk.end_page,
        metadata=chunk.chunk_metadata,
    )
