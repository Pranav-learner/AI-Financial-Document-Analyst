"""Query Classifier and Planner nodes (Phase 7).

Classifies user query intent and maps it to a logical list of tools.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.financial_analyst.state import AgentState
from app.agents.financial_analyst.exceptions import IntentClassificationException, PlannerException
from app.agents.financial_analyst.validators import validate_intent_classification, validate_planning
from app.agents.financial_analyst.models import _INTENT_SCHEMA, _PLAN_SCHEMA
from app.agents.financial_analyst.utils import retry_gemini

log = get_logger(__name__)


class QueryClassifier:
    """Classifies user query intent."""

    def __init__(self, client: genai.Client | None = None) -> None:
        self.api_key = settings.gemini_api_key
        self._client = client
        self.model = settings.gemini_llm_model

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def classify(self, state: AgentState) -> dict[str, Any]:
        """Classify user query intent using Gemini."""
        validate_intent_classification(state)
        query = state["query"]
        history = state.get("history") or []
        company_id = state.get("company_id")

        history_str = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in history]
        )

        prompt = (
            "You are a financial analyst assistant. Classify the following query into exactly one of these intents:\n"
            "- RAG_RETRIEVAL: general financial Q&A that requires retrieving documents and reading chunks.\n"
            "- METRIC_EXTRACTION: query specifically about retrieving specific numerical financial metrics for a company/report.\n"
            "- PERIOD_COMPARISON: query that asks to compare metrics or performance between two periods (YoY, QoQ).\n"
            "- RISK_ANALYSIS: query asking about risks, risk factors, or risk evolution.\n"
            "- TONE_ANALYSIS: query about management tone, sentiment, or tone evolution in prepared remarks/commentary.\n"
            "- HEALTH_CHECK: simple system health, ping, or greetings.\n"
            "- GENERAL_QA: generic non-financial or conversational question.\n\n"
            f"Conversation History:\n{history_str}\n\n"
            f"Active Company ID context: {company_id}\n"
            f"QUERY: \"{query}\"\n"
        )

        try:
            client = self._get_client()
            resp = await retry_gemini(
                lambda: client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_INTENT_SCHEMA,
                        temperature=0.0,
                    ),
                )
            )
            raw_text = resp.text or "{}"
            data = json.loads(raw_text)
            intent = data.get("intent", "RAG_RETRIEVAL")
            log.info("query_classifier.success", intent=intent, confidence=data.get("confidence"))
            return {"intent": intent}
        except Exception as exc:
            log.error("query_classifier.error", error=str(exc))
            # Fallback to RAG_RETRIEVAL to be robust
            return {"intent": "RAG_RETRIEVAL", "errors": state.get("errors", []) + [f"Intent classification error: {exc}"]}


class Planner:
    """Generates a structured plan containing tool executions."""

    def __init__(self, client: genai.Client | None = None) -> None:
        self.api_key = settings.gemini_api_key
        self._client = client
        self.model = settings.gemini_llm_model

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def build_plan(self, state: AgentState) -> dict[str, Any]:
        """Build execution plan using Gemini based on query and classified intent."""
        validate_planning(state)
        query = state["query"]
        intent = state["intent"]
        company_id = state.get("company_id")
        report_id = state.get("report_id")
        history = state.get("history") or []

        history_str = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in history]
        )

        # Build context section — tell the LLM exactly which IDs to use
        context_lines = []
        if report_id:
            context_lines.append(f"Active Report ID (MUST pass as report_id in retrieve_evidence): {report_id}")
        if company_id:
            context_lines.append(f"Active Company ID: {company_id}")
        context_block = "\n".join(context_lines) if context_lines else "No specific report or company context provided."

        prompt = (
            "You are a financial analyst planner. Create a list of tool steps needed to answer the user query.\n"
            f"Query: \"{query}\"\n"
            f"Classified Intent: {intent}\n\n"
            f"Context:\n{context_block}\n\n"
            "Available tools:\n"
            "- get_financial_metrics: args { company_id: str, report_id: str }\n"
            "- get_metric_comparisons: args { company_id: str, report_id: str }\n"
            "- get_financial_analytics: args { company_id: str, report_id: str }\n"
            "- get_risk_factors: args { company_id: str, report_id: str }\n"
            "- get_risk_evolution: args { company_id: str }\n"
            "- get_management_tone: args { company_id: str, report_id: str }\n"
            "- get_tone_evolution: args { company_id: str }\n"
            "- retrieve_evidence: args { query: str, company_id: str, report_id: str, top_k: int }\n\n"
            "Rules:\n"
            "1. ONLY output tools listed above.\n"
            "2. For ANY query about a specific report's content (net sales, assets, financials, risks, text), you MUST call retrieve_evidence.\n"
            "3. ALWAYS pass report_id and company_id from the Context section into the arguments of retrieve_evidence and other tools — do not omit them if provided.\n"
            "4. For general QA or health check, you can return an empty list of steps.\n"
            "5. retrieve_evidence retrieves raw text from the uploaded PDF — always use it for factual document questions.\n"
        )

        try:
            client = self._get_client()
            resp = await retry_gemini(
                lambda: client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_PLAN_SCHEMA,
                        temperature=0.0,
                    ),
                )
            )
            raw_text = resp.text or "{}"
            data = json.loads(raw_text)
            steps = data.get("steps", [])
            log.info("planner.success", steps_count=len(steps), report_id=str(report_id), company_id=str(company_id))
            return {"plan": steps}
        except Exception as exc:
            log.error("planner.error", error=str(exc))
            # Fallback plan: run retrieve_evidence with all available context
            fallback_step = {
                "tool_name": "retrieve_evidence",
                "arguments": {
                    "query": query,
                    "company_id": str(company_id) if company_id else None,
                    "report_id": str(report_id) if report_id else None,
                    "top_k": 10
                }
            }
            return {"plan": [fallback_step], "errors": state.get("errors", []) + [f"Planning error: {exc}"]}
