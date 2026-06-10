"""ORM model registry.

Importing this package registers all models on `Base.metadata` so Alembic
autogenerate and relationship resolution see them. Add new models here per phase.
"""

from app.models.company import Company
from app.models.document_chunk import DocumentChunk
from app.models.enums import ReportStatus, ReportType
from app.models.report import Report
from app.models.report_page import ReportPage
from app.models.report_section import ReportSection

__all__ = [
    "Company",
    "DocumentChunk",
    "Report",
    "ReportPage",
    "ReportSection",
    "ReportStatus",
    "ReportType",
]
