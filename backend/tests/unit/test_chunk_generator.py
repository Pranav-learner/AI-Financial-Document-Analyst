"""Unit tests for the chunk generation orchestrator (incl. metadata + dedupe)."""

from __future__ import annotations

import pytest

from app.ingestion.chunking import ChunkGenerator, ReportContext, SectionInput
from app.ingestion.chunking.chunk_validation import REQUIRED_METADATA_KEYS

REPORT = ReportContext(
    report_id="r1", report_type="10-K", year=2025, quarter=None, company="ACME"
)


def _section(sid: str, name: str, content: str, sp: int = 1, ep: int = 1) -> SectionInput:
    return SectionInput(
        section_id=sid, section_name=name, normalized_section_name=name,
        start_page=sp, end_page=ep, content=content,
    )


@pytest.mark.unit
def test_chunk_index_is_sequential_and_metadata_complete() -> None:
    sections = [
        _section("s1", "Risk Factors", "Risk one. " * 200, sp=3, ep=5),
        _section("s2", "MD&A", "Revenue discussion. " * 200, sp=6, ep=9),
    ]
    chunks = ChunkGenerator().generate(REPORT, sections)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    for c in chunks:
        assert REQUIRED_METADATA_KEYS <= set(c.metadata.keys())
        assert c.metadata["company"] == "ACME"
        assert c.metadata["report_id"] == "r1"
        assert c.token_count > 0
    # Section page span is propagated to its chunks.
    rf = [c for c in chunks if c.metadata["normalized_section_name"] == "Risk Factors"]
    assert all(c.start_page == 3 and c.end_page == 5 for c in rf)


@pytest.mark.unit
def test_duplicate_content_across_sections_is_deduped() -> None:
    content = "Identical boilerplate paragraph. " * 100
    one = ChunkGenerator().generate(REPORT, [_section("s1", "MD&A", content)])
    two = ChunkGenerator().generate(
        REPORT,
        [_section("s1", "MD&A", content), _section("s2", "Management Commentary", content)],
    )
    # The second identical section produces no new chunks (all duplicates dropped).
    assert len(two) == len(one)


@pytest.mark.unit
def test_generation_is_deterministic() -> None:
    sections = [_section("s1", "MD&A", "Sentence here. " * 300)]
    a = ChunkGenerator().generate(REPORT, sections)
    b = ChunkGenerator().generate(REPORT, sections)
    assert [c.chunk_text for c in a] == [c.chunk_text for c in b]


@pytest.mark.unit
def test_empty_sections_produce_no_chunks() -> None:
    assert ChunkGenerator().generate(REPORT, [_section("s1", "MD&A", "   ")]) == []
