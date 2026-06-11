"""LLM-based memo generation builder for Phase 9: Investment Memo."""

from __future__ import annotations

import json
import uuid
from typing import Any
from google import genai
from google.genai import types

from app.core.config import settings as app_settings
from app.core.logging import get_logger
from app.memo.exceptions import MemoGenerationError
from app.memo.memo_models import (
    MemoPackage,
    MemoSectionSchema,
    CitationSchema,
)
from app.memo.citation_builder import CitationBuilder
from app.memo.company_overview_builder import CompanyOverviewBuilder
from app.memo.financial_summary_builder import FinancialSummaryBuilder
from app.memo.risk_summary_builder import RiskSummaryBuilder
from app.memo.management_summary_builder import ManagementSummaryBuilder
from app.memo.benchmark_summary_builder import BenchmarkSummaryBuilder
from app.memo.bull_case_generator import BullCaseGenerator
from app.memo.bear_case_generator import BearCaseGenerator
from app.memo.question_generator import QuestionGenerator

log = get_logger(__name__)

_MEMO_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING"},
        "executive_summary": {"type": "STRING"},
        "sections": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "section_name": {"type": "STRING"},
                    "section_order": {"type": "INTEGER"},
                    "content": {"type": "STRING"},
                    "citations": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "chunk_id": {"type": "STRING"},
                                "page_number": {"type": "INTEGER"},
                                "section_name": {"type": "STRING"},
                                "source_type": {"type": "STRING"},
                                "text_snippet": {"type": "STRING"}
                            },
                            "required": ["source_type"]
                        }
                    }
                },
                "required": ["section_name", "section_order", "content"]
            }
        }
    },
    "required": ["title", "executive_summary", "sections"]
}


class MemoBuilder:
    """Invokes Gemini 2.5 Pro or uses deterministic template fallback to build the investment memo."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or app_settings.gemini_api_key
        # Use gemini-2.5-pro as requested by Phase 9 requirements, falling back to app settings model if not specified.
        self.model = model or "gemini-2.5-pro"
        self._client = None

    def _get_client(self) -> genai.Client | None:
        if not self.api_key:
            return None
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, package: MemoPackage) -> dict[str, Any]:
        """Generates the investment memo contents (either via LLM or rule-based fallback)."""
        client = self._get_client()
        if not client:
            log.warning("memo_builder.generate_fallback", reason="No Gemini API key supplied. Executing rule-based fallback.")
            return self.generate_fallback_memo(package)

        prompt = self._build_prompt(package)

        try:
            resp = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_MEMO_RESPONSE_SCHEMA,
                    temperature=0.1,
                ),
            )
            raw_text = resp.text or "{}"
            return self._parse_and_validate_response(raw_text, package)
        except Exception as exc:
            log.error("memo_builder.generate_llm_failed", error=str(exc))
            return self.generate_fallback_memo(package)

    def _build_prompt(self, package: MemoPackage) -> str:
        # Construct specific segments using context builders
        overview_ctx = CompanyOverviewBuilder().build_context_prompt(package)
        financial_ctx = FinancialSummaryBuilder().build_context_prompt(package)
        risk_ctx = RiskSummaryBuilder().build_context_prompt(package)
        management_ctx = ManagementSummaryBuilder().build_context_prompt(package)
        benchmark_ctx = BenchmarkSummaryBuilder().build_context_prompt(package)
        bull_ctx = BullCaseGenerator().build_context_prompt(package)
        bear_ctx = BearCaseGenerator().build_context_prompt(package)
        question_ctx = QuestionGenerator().build_context_prompt(package)

        return (
            "You are a Lead Financial AI Analyst. Generate a professional, structured investment memo "
            f"for {package.company_name} based on the structured intelligence package provided below.\n\n"
            "## CRITICAL INSTRUCTIONS & GUARDRAILS:\n"
            "1. GROUNDING RULE: Under no circumstances may you invent or extrapolate numerical figures not present in the input MemoPackage. Every number must match the source data exactly.\n"
            "2. NEGATIVE CONSTRAINTS: Do NOT include any stock ratings (e.g. buy, sell, hold), price targets, portfolio allocations, or buy/sell recommendations. Focus strictly on evidence-backed analysis.\n"
            "3. CITATIONS: Include precise citations inside the 'citations' array of each section. Provide the chunk_id, page_number, and source_type ('text_chunk', 'financial_metric', 'risk_factor', or 'management_tone') for every statement you make.\n\n"
            "## STRUCTURED INTEL PACKAGE:\n"
            f"=== 1. Company and Report Overview ===\n{overview_ctx}\n"
            f"=== 2. Financial Metrics & Performance ===\n{financial_ctx}\n"
            f"=== 3. Risk Intelligence ===\n{risk_ctx}\n"
            f"=== 4. Management Commentary & Tone ===\n{management_ctx}\n"
            f"=== 5. Cohort Benchmarking ===\n{benchmark_ctx}\n"
            f"=== 6. Bull Case Arguments ===\n{bull_ctx}\n"
            f"=== 7. Bear Case Arguments ===\n{bear_ctx}\n"
            f"=== 8. Due Diligence Questions ===\n{question_ctx}\n\n"
            "Produce a JSON object conforming exactly to the requested schema. Build exactly 8 sections in the 'sections' array, matching the 8 components above, ordered 1 through 8."
        )

    def _parse_and_validate_response(self, raw_json: str, package: MemoPackage) -> dict[str, Any]:
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise MemoGenerationError(f"LLM returned invalid JSON: {exc}")

        title = data.get("title") or f"Investment Memo: {package.company_name}"
        exec_summary = data.get("executive_summary") or "Executive Summary"
        raw_sections = data.get("sections") or []

        citation_builder = CitationBuilder(package)
        parsed_sections = []

        for rs in raw_sections:
            sec_name = rs.get("section_name", "General Section")
            sec_order = rs.get("section_order", 0)
            content = rs.get("content", "")
            raw_citations = rs.get("citations") or []

            # Resolve citations via Jaccard lookup / package verification
            resolved_citations = citation_builder.resolve_and_validate(raw_citations)

            parsed_sections.append(
                MemoSectionSchema(
                    section_name=sec_name,
                    section_order=sec_order,
                    content=content,
                    citations=resolved_citations,
                )
            )

        return {
            "title": title,
            "executive_summary": exec_summary,
            "sections": parsed_sections
        }

    def generate_fallback_memo(self, package: MemoPackage) -> dict[str, Any]:
        """Deterministic rule-based fallback generator when LLM is unavailable or fails."""
        log.info("memo_builder.generating_fallback_narratives", company=package.company_name)

        title = f"Investment Memo: {package.company_name} ({package.reporting_period} {package.reporting_year})"
        exec_summary = (
            f"This structured investment memo compiles relational intelligence for {package.company_name} "
            f"based on the {package.report_title}. Key findings highlight financial metrics, "
            f"risk profiles, management commentary tone, and competitive benchmarking performance."
        )

        builders = [
            ("Company Overview", CompanyOverviewBuilder()),
            ("Financial Summary", FinancialSummaryBuilder()),
            ("Risk Summary", RiskSummaryBuilder()),
            ("Management Assessment", ManagementSummaryBuilder()),
            ("Competitive Position", BenchmarkSummaryBuilder()),
            ("Bull Case", BullCaseGenerator()),
            ("Bear Case", BearCaseGenerator()),
            ("Questions to Investigate", QuestionGenerator()),
        ]

        sections = []
        for index, (name, builder) in enumerate(builders, start=1):
            content = builder.generate_fallback(package)
            
            # Simple fallback citation matching the first chunk
            citations = []
            if package.retrieved_evidence:
                first_chunk = package.retrieved_evidence[0]
                citations.append(
                    CitationSchema(
                        report_id=package.report_id,
                        chunk_id=first_chunk.id,
                        page_number=first_chunk.page_number,
                        section_name=first_chunk.section_name or "Overview",
                        source_type="text_chunk",
                        text_snippet=first_chunk.content[:200],
                    )
                )

            sections.append(
                MemoSectionSchema(
                    section_name=name,
                    section_order=index,
                    content=content,
                    citations=citations
                )
            )

        return {
            "title": title,
            "executive_summary": exec_summary,
            "sections": sections
        }
