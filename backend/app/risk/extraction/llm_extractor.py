"""LLM-assisted risk extraction (Phase 4).

Uses Gemini (gemini-2.5-pro) with **structured output only** (JSON schema), per
candidate chunk so each result is attributable to a `source_chunk_id`. The LLM is
an assistant, never the source of truth: we validate and normalize the results
deterministically before saving.

Degrades gracefully: with no API key (or on terminal failure) it returns an empty
list and logs.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from app.core.config import settings as app_settings
from app.core.logging import get_logger
from app.risk.extraction.exceptions import (
    RiskLLMError,
    RiskLLMResponseError,
    RiskLLMTransientError,
)
from app.risk.extraction.extraction_models import RiskCandidate, RiskChunkInput
from app.risk.taxonomy.normalization import normalize_category, normalize_risk_name, normalize_description, normalize_severity
from app.risk.taxonomy.risk_categories import get_risk_taxonomy

log = get_logger(__name__)

_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "risk_name": {"type": "STRING"},
            "risk_description": {"type": "STRING"},
            "category": {"type": "STRING"},
            "severity": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["risk_name", "risk_description", "category", "severity"],
    },
}


class RiskLLMExtractor:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_retries: int = 3,
        base_delay: float = 2.0,
        timeout: float = 60.0,
        client: object | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._timeout = timeout
        self._client = client
        self._sleep = sleep
        self.taxonomy = get_risk_taxonomy()

    @classmethod
    def from_settings(cls, *, client: object | None = None) -> RiskLLMExtractor:
        return cls(
            api_key=app_settings.gemini_api_key,
            model=app_settings.gemini_llm_model,
            max_retries=app_settings.metric_llm_max_retries,
            base_delay=app_settings.metric_llm_retry_base_delay,
            timeout=app_settings.metric_llm_request_timeout,
            client=client,
        )

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    def extract(self, chunks: list[RiskChunkInput]) -> list[RiskCandidate]:
        if not self.enabled:
            log.warning("risk_extraction.llm_disabled", reason="no GEMINI_API_KEY; rule-only")
            return []
        out: list[RiskCandidate] = []
        for ch in chunks:
            try:
                raw = self._with_retries(lambda text=ch.text: self._generate(text))
                out.extend(self._parse(raw, ch))
            except RiskLLMError as exc:
                log.error("risk_extraction.llm_chunk_failed", chunk_id=ch.chunk_id, error=str(exc))
        return out

    def _build_prompt(self, text: str) -> str:
        categories = ", ".join(self.taxonomy.all_categories())
        return (
            "Extract distinct business/financial/operational risks mentioned in the text below.\n"
            f"Classify each risk into one of these canonical categories: {categories}.\n"
            "Assign a severity level: LOW, MEDIUM, HIGH, or CRITICAL.\n"
            "Provide a concise name/title for the risk (less than 10 words) and a detailed description of the risk.\n"
            "Return the list of extracted risks matching the requested schema.\n\n"
            f"TEXT:\n{text}"
        )

    def _get_client(self) -> object:
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _generate(self, text: str) -> str:
        if app_settings.demo_mode:
            return json.dumps([
                {
                    "risk_name": "Currency Fluctuation Risk",
                    "risk_description": "Exposure to foreign exchange volatility affecting international sales and profits.",
                    "category": "Market Risk",
                    "severity": "HIGH",
                    "confidence": 0.85
                }
            ])

        from google.genai import types

        client = self._get_client()
        try:
            resp = client.models.generate_content(  # type: ignore[attr-defined]
                model=self._model,
                contents=self._build_prompt(text),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_RESPONSE_SCHEMA,
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            raise self._classify(exc) from exc
        return resp.text or "[]"

    def _with_retries(self, call: Callable[[], str]) -> str:
        attempt = 0
        while True:
            try:
                return call()
            except RiskLLMError as exc:
                if not getattr(exc, "retryable", False) or attempt >= self._max_retries:
                    raise
                delay = self._base_delay * (2 ** attempt)
                attempt += 1
                log.warning("risk_extraction.llm_retry", attempt=attempt, error=str(exc))
                self._sleep(delay)

    @staticmethod
    def _classify(exc: Exception) -> RiskLLMError:
        msg = str(exc).lower()
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if code == 429 or "rate limit" in msg or "resource_exhausted" in msg or "quota" in msg:
            return RiskLLMTransientError(str(exc))
        if (isinstance(code, int) and code >= 500) or "timeout" in msg or "unavailable" in msg:
            return RiskLLMTransientError(str(exc))
        return RiskLLMError(str(exc))

    def _parse(self, raw: str, ch: RiskChunkInput) -> list[RiskCandidate]:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RiskLLMResponseError(f"invalid JSON from LLM: {exc}") from exc
        if not isinstance(items, list):
            raise RiskLLMResponseError("LLM response is not a JSON array")

        out: list[RiskCandidate] = []
        for item in items:
            cand = self._to_candidate(item, ch)
            if cand is not None:
                out.append(cand)
        return out

    def _to_candidate(self, item: dict, ch: RiskChunkInput) -> RiskCandidate | None:
        if not isinstance(item, dict):
            return None
        raw_name = str(item.get("risk_name", "")).strip()
        if not raw_name:
            return None

        norm_name = normalize_risk_name(raw_name)
        desc = normalize_description(str(item.get("risk_description", "")))
        category = normalize_category(item.get("category"), desc, self.taxonomy)
        severity = normalize_severity(str(item.get("severity", "MEDIUM")))
        
        try:
            raw_conf = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            raw_conf = 0.7

        is_risk_section = False
        norm_sec = (ch.normalized_section_name or "").upper()
        if norm_sec in ("RISK FACTORS", "MD&A", "FORWARD GUIDANCE", "FORWARD-LOOKING STATEMENTS"):
            is_risk_section = True

        return RiskCandidate(
            risk_name=raw_name,
            normalized_risk_name=norm_name,
            risk_description=desc,
            category=category,
            severity=severity,
            source_chunk_id=ch.chunk_id,
            source_text=ch.text[:300].strip(),
            method="LLM_BASED",
            raw_confidence=max(0.0, min(1.0, raw_conf)),
            section_match=is_risk_section,
            extraction_metadata={
                "llm_suggested_category": item.get("category"),
                "llm_suggested_severity": item.get("severity"),
            }
        )
