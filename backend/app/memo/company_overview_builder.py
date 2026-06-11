"""Company overview section builder for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class CompanyOverviewBuilder:
    """Builds prompt context and fallback template for Company Overview section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures report metadata and retrieved RAG context for the prompt."""
        chunks_text = "\n".join(
            [f"- [Doc Chunk {c.id} Page {c.page_number}]: {c.content}" for c in package.retrieved_evidence[:5]]
        )
        return (
            f"Company Name: {package.company_name}\n"
            f"Report Title: {package.report_title}\n"
            f"Period: {package.reporting_period} {package.reporting_year}\n"
            f"Relevant Document Passages:\n{chunks_text}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative."""
        overview = (
            f"This section provides an overview of {package.company_name} based on its "
            f"{package.report_title} for {package.reporting_period} {package.reporting_year}."
        )
        if package.retrieved_evidence:
            overview += f" The source report details are extracted from the primary document text (e.g., page {package.retrieved_evidence[0].page_number})."
        return overview
