"""Query classification and rewriting models."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class QueryClass(str, Enum):
    FINANCIAL_METRIC = "FINANCIAL_METRIC"
    RISK = "RISK"
    TONE = "TONE"
    GUIDANCE = "GUIDANCE"
    GENERAL = "GENERAL"
    MIXED = "MIXED"


class QueryClassificationResult(BaseModel):
    query: str
    predicted_class: QueryClass
    confidence: float
    reasoning: str


class QueryRewriteResult(BaseModel):
    original_query: str
    rewritten_query: str
    sub_queries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    query_class: QueryClass
