"""Orchestrator for Phase 9: Investment Memo Generation Engine."""

from __future__ import annotations

import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models.memo import InvestmentMemo, MemoSection
from app.models.enums import MemoStatus, MemoType
from app.memo.exceptions import MemoError, MemoValidationError
from app.memo.memo_package_builder import MemoPackageBuilder
from app.memo.memo_builder import MemoBuilder
from app.memo.memo_validator import MemoValidator
from app.core.logging import get_logger

log = get_logger(__name__)


class MemoOrchestrator:
    """Manages transactional state and orchestration of the investment memo lifecycle."""

    def __init__(self, db: Session):
        self.db = db

    def initiate_memo(
        self,
        company_id: uuid.UUID,
        report_id: uuid.UUID,
        benchmark_run_id: uuid.UUID | None = None,
        memo_type: MemoType = MemoType.SINGLE_COMPANY,
        title: str | None = None
    ) -> InvestmentMemo:
        """Creates an initial InvestmentMemo record in PENDING state."""
        memo_title = title or f"Investment Memo (Pending Generation)"
        
        memo = InvestmentMemo(
            company_id=company_id,
            report_id=report_id,
            benchmark_run_id=benchmark_run_id,
            memo_type=memo_type,
            status=MemoStatus.PENDING,
            title=memo_title,
            metadata_fields={"initialized_at": uuid.uuid4().hex}
        )
        self.db.add(memo)
        self.db.commit()
        self.db.refresh(memo)
        return memo

    def generate_memo_sync(self, memo_id: uuid.UUID) -> InvestmentMemo:
        """Executes the full memo generation pipeline synchronously."""
        # 1. Load Memo
        memo = self.db.scalar(select(InvestmentMemo).where(InvestmentMemo.id == memo_id))
        if not memo:
            raise MemoError(f"Memo not found: {memo_id}")

        # Update status to GENERATING
        memo.status = MemoStatus.GENERATING
        self.db.commit()
        self.db.refresh(memo)

        try:
            # 2. Build Package
            package_builder = MemoPackageBuilder(self.db)
            package = package_builder.build(
                company_id=memo.company_id,
                report_id=memo.report_id,
                benchmark_run_id=memo.benchmark_run_id
            )

            # 3. Generate content via LLM/Fallback
            builder = MemoBuilder()
            generated = builder.generate(package)

            # 4. Post-generation validation
            validator = MemoValidator()
            validator.validate(
                package=package,
                executive_summary=generated["executive_summary"],
                sections=generated["sections"]
            )

            # 5. Persist the generated sections and update parent memo details
            memo.title = generated.get("title") or memo.title
            memo.executive_summary = generated["executive_summary"]
            memo.status = MemoStatus.COMPLETED

            # Delete any existing sections (to keep generation idempotent)
            self.db.execute(delete(MemoSection).where(MemoSection.memo_id == memo.id))

            # Add new sections
            markdown_content_list = []
            for sec_schema in generated["sections"]:
                section = MemoSection(
                    memo_id=memo.id,
                    section_name=sec_schema.section_name,
                    section_order=sec_schema.section_order,
                    content=sec_schema.content,
                    citations=[c.model_dump(mode="json") for c in sec_schema.citations],
                )
                self.db.add(section)
                
                # Format section into compiling full markdown
                citations_md = ""
                if sec_schema.citations:
                    citations_list = []
                    for idx, cit in enumerate(sec_schema.citations, start=1):
                        snippet = f' - "{cit.text_snippet[:60]}..."' if cit.text_snippet else ""
                        page_str = f" Page {cit.page_number}" if cit.page_number else ""
                        citations_list.append(f"[{idx}] {cit.source_type.title()}{page_str}{snippet}")
                    citations_md = "\n\n**Citations:**\n" + "\n".join(citations_list)

                markdown_content_list.append(
                    f"## {sec_schema.section_name}\n\n{sec_schema.content}{citations_md}"
                )

            # Join compiled markdown content
            memo.content = f"# {memo.title}\n\n## Executive Summary\n\n{memo.executive_summary}\n\n" + "\n\n".join(markdown_content_list)
            
            # Record success metadata
            memo.metadata_fields = {
                **memo.metadata_fields,
                "generated_at": uuid.uuid4().hex,
                "sections_count": len(generated["sections"]),
                "success": True
            }

            self.db.commit()
            self.db.refresh(memo)
            log.info("memo_orchestrator.generate_success", memo_id=memo.id)
            return memo

        except Exception as exc:
            # Handle failure cases gracefully, persisting FAILED status
            log.error("memo_orchestrator.generate_failed", memo_id=memo.id, error=str(exc))
            self.db.rollback()

            # We reload the memo object in a clean transaction session to update status to FAILED
            memo = self.db.scalar(select(InvestmentMemo).where(InvestmentMemo.id == memo_id))
            if memo:
                memo.status = MemoStatus.FAILED
                memo.metadata_fields = {
                    **memo.metadata_fields,
                    "error_message": str(exc),
                    "failed_at": uuid.uuid4().hex,
                    "success": False
                }
                self.db.commit()
                self.db.refresh(memo)

            # Re-raise to let caller handle if they wish
            raise
