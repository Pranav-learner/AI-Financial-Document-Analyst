"""Query classification engine (Phase 6)."""

from __future__ import annotations

import json
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.query_rewriting.models import QueryClass, QueryClassificationResult
from app.rag.query_rewriting.exceptions import QueryClassifierError

log = get_logger(__name__)

_CLASSIFY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "predicted_class": {
            "type": "STRING",
            "enum": ["FINANCIAL_METRIC", "RISK", "TONE", "GUIDANCE", "GENERAL", "MIXED"]
        },
        "confidence": {"type": "NUMBER"},
        "reasoning": {"type": "STRING"}
    },
    "required": ["predicted_class", "confidence", "reasoning"]
}


class FinancialQueryClassifier:
    """Classifies a financial query to determine downstream retrieval strategy."""

    def __init__(self, *, client: genai.Client | None = None) -> None:
        self.api_key = settings.gemini_api_key
        self._client = client
        self.model = settings.gemini_llm_model

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def classify(self, query: str) -> QueryClassificationResult:
        if not query or not query.strip():
            raise QueryClassifierError("Cannot classify an empty query")

        cleaned = query.strip()

        # Try LLM classification if API key is provided
        if self.api_key:
            try:
                client = self._get_client()
                prompt = (
                    "Classify the following financial query into exactly one of these classes:\n"
                    "- FINANCIAL_METRIC: queries about revenue, operating margin, cash flow, Capex, EBITDA, and financial statements.\n"
                    "- RISK: queries about supply chain, cybersecurity, concentration, regulations, lawsuits, and other risks.\n"
                    "- TONE: queries about management sentiment, confidence levels, hedging, transcripts, prepared remarks, Q&A.\n"
                    "- GUIDANCE: queries about future outlook, forward guidance, predictions, and upcoming fiscal years.\n"
                    "- GENERAL: general company overview, business description, executive names, and basic corporate facts.\n"
                    "- MIXED: queries that combine two or more of the categories above.\n\n"
                    f"QUERY: \"{cleaned}\"\n"
                )
                resp = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_CLASSIFY_SCHEMA,
                        temperature=0.0
                    )
                )
                raw_text = resp.text or "{}"
                data = json.loads(raw_text)
                return QueryClassificationResult(
                    query=cleaned,
                    predicted_class=QueryClass(data["predicted_class"]),
                    confidence=max(0.0, min(1.0, float(data.get("confidence", 1.0)))),
                    reasoning=data.get("reasoning", "LLM classified")
                )
            except Exception as exc:
                log.warning("query_classification.llm_failed", error=str(exc))
                # Fall back to local rule-based classification

        # Local fallback classification
        return self._classify_local(cleaned)

    def _classify_local(self, query: str) -> QueryClassificationResult:
        lowered = query.lower()

        # Score matching
        scores = {
            QueryClass.FINANCIAL_METRIC: 0,
            QueryClass.RISK: 0,
            QueryClass.TONE: 0,
            QueryClass.GUIDANCE: 0,
            QueryClass.GENERAL: 0,
        }

        # Financial keywords
        fin_keywords = {"revenue", "margin", "cash flow", "capex", "capital expenditure", "ebitda", "profit", "sales", "income", "balance sheet", "net income", "debt"}
        for k in fin_keywords:
            if k in lowered:
                scores[QueryClass.FINANCIAL_METRIC] += 2

        # Risk keywords
        risk_keywords = {"risk", "threat", "concern", "supply chain", "cybersecurity", "breach", "lawsuit", "regulation", "legal", "uncertainty", "litigation", "competitor"}
        for k in risk_keywords:
            if k in lowered:
                scores[QueryClass.RISK] += 2

        # Tone keywords
        tone_keywords = {"sentiment", "tone", "management discussion", "md&a", "transcript", "prepared remarks", "q&a", "call", "optimistic", "pessimistic", "hedging", "confidence"}
        for k in tone_keywords:
            if k in lowered:
                scores[QueryClass.TONE] += 2

        # Guidance keywords
        guidance_keywords = {"guidance", "outlook", "future", "forecast", "projection", "expect", "predict", "next year", "upcoming"}
        for k in guidance_keywords:
            if k in lowered:
                scores[QueryClass.GUIDANCE] += 2

        # General keywords
        general_keywords = {"overview", "business description", "company description", "who is", "what does", "ceo", "board of directors", "headquarters"}
        for k in general_keywords:
            if k in lowered:
                scores[QueryClass.GENERAL] += 1

        # Check top class
        sorted_classes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_class, top_score = sorted_classes[0]

        # Mixed detection
        active_classes = [c for c, s in scores.items() if s > 1]

        if len(active_classes) >= 2:
            return QueryClassificationResult(
                query=query,
                predicted_class=QueryClass.MIXED,
                confidence=0.7,
                reasoning=f"Detected multiple intents locally: {', '.join([c.value for c in active_classes])}"
            )

        if top_score == 0:
            return QueryClassificationResult(
                query=query,
                predicted_class=QueryClass.GENERAL,
                confidence=0.5,
                reasoning="No specific keywords matched, defaulted to general."
            )

        return QueryClassificationResult(
            query=query,
            predicted_class=top_class,
            confidence=0.85,
            reasoning=f"Matched local keywords for class {top_class.value}"
        )
