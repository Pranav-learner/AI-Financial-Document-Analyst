"""Query rewriting engine (Phase 6)."""

from __future__ import annotations

import json
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.query_rewriting.models import QueryClass, QueryRewriteResult
from app.rag.query_rewriting.query_classifier import FinancialQueryClassifier
from app.rag.query_rewriting.rewrite_strategies import STRATEGY_PROMPTS
from app.rag.query_rewriting.validators import validate_query
from app.rag.query_rewriting.exceptions import QueryRewriterError

log = get_logger(__name__)

_REWRITE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "rewritten_query": {"type": "STRING"},
        "sub_queries": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        },
        "keywords": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        }
    },
    "required": ["rewritten_query", "sub_queries", "keywords"]
}


class QueryRewriter:
    """Rewrites user queries into keyword-expanded and sub-query variants for retrieval."""

    def __init__(
        self,
        *,
        client: genai.Client | None = None,
        classifier: FinancialQueryClassifier | None = None
    ) -> None:
        self.api_key = settings.gemini_api_key
        self._client = client
        self.model = settings.gemini_llm_model
        self.classifier = classifier or FinancialQueryClassifier(client=client)

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def rewrite(self, query: str) -> QueryRewriteResult:
        # 1. Validate query
        cleaned = validate_query(query)

        # 2. Classify query
        class_res = self.classifier.classify(cleaned)
        q_class = class_res.predicted_class

        # 3. Rewrite query using LLM if enabled
        if self.api_key:
            try:
                strategy_instruction = STRATEGY_PROMPTS[q_class]
                prompt = (
                    f"You are an expert financial retrieval engine query rewriter.\n"
                    f"Your goal is to rewrite the input query into a keyword-expanded search query optimized for vector and hybrid search.\n"
                    f"If the query contains multiple distinct topics/questions, break them down into separate 'sub_queries'.\n"
                    f"The query was classified as: {q_class.value}.\n"
                    f"Strategy instruction: {strategy_instruction}\n\n"
                    f"INPUT QUERY: \"{cleaned}\"\n"
                )

                client = self._get_client()
                resp = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_REWRITE_SCHEMA,
                        temperature=0.0
                    )
                )
                raw_text = resp.text or "{}"
                data = json.loads(raw_text)

                return QueryRewriteResult(
                    original_query=cleaned,
                    rewritten_query=data["rewritten_query"].strip(),
                    sub_queries=[q.strip() for q in data.get("sub_queries", []) if q.strip()],
                    keywords=[k.strip() for k in data.get("keywords", []) if k.strip()],
                    query_class=q_class
                )
            except Exception as exc:
                log.warning("query_rewriter.llm_failed", error=str(exc))
                # Fall back to local rules

        # Fallback local query rewriter rules
        return self._rewrite_local(cleaned, q_class)

    def _rewrite_local(self, query: str, q_class: QueryClass) -> QueryRewriteResult:
        # Basic splitting logic for sub-queries
        # e.g., "How did revenue and cash flow change?" -> ["revenue change", "cash flow change"]
        sub_queries = []
        lowered = query.lower()
        if " and " in lowered:
            parts = query.split(" and ")
            for part in parts:
                sub_queries.append(part.strip())
        elif " or " in lowered:
            parts = query.split(" or ")
            for part in parts:
                sub_queries.append(part.strip())

        if not sub_queries:
            sub_queries = [query]

        # Basic keyword extraction & expansion
        words = [w.strip("?,.!:;\"'") for w in query.split()]
        stop_words = {"what", "are", "is", "how", "did", "the", "company", "in", "of", "for", "with", "a", "an", "on", "to", "by"}
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 2]

        # Apply specific expansions by class
        expansion_terms = []
        if q_class == QueryClass.FINANCIAL_METRIC:
            expansion_terms = ["revenue", "operating margin", "cash flow", "capital expenditure", "EBITDA"]
        elif q_class == QueryClass.RISK:
            expansion_terms = ["supply chain risk", "regulatory disruption", "cybersecurity", "operational vulnerability"]
        elif q_class == QueryClass.TONE:
            expansion_terms = ["management tone", "prepared remarks sentiment", "optimism level", "hedging score"]
        elif q_class == QueryClass.GUIDANCE:
            expansion_terms = ["forward guidance", "outlook projection", "future target", "forecast expectations"]
        else:
            expansion_terms = ["operational performance", "overview profile", "business description"]

        # Blend keywords with original query words for rewritten string
        unique_expanded = list(dict.fromkeys(keywords + expansion_terms))
        rewritten = " ".join(unique_expanded)

        return QueryRewriteResult(
            original_query=query,
            rewritten_query=rewritten,
            sub_queries=sub_queries,
            keywords=keywords,
            query_class=q_class
        )
