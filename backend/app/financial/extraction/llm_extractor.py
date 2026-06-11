"""LLM-assisted metric extraction (Phase 3A, task §5).

Uses Gemini (gemini-2.5-pro) with **structured output only** (JSON schema), per
candidate chunk so each result is attributable to a `source_chunk_id`. The LLM is
an *assistant*, never the source of truth: it returns the raw number + unit it
read, and WE compute the normalized value deterministically (ADR-007/ADR-017).

Degrades gracefully: with no API key (or on terminal failure) it returns an empty
list and logs — so hybrid extraction falls back to rule-only and the pipeline
never breaks. The SDK is lazy-imported; tests override `_generate`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from decimal import Decimal, InvalidOperation

from app.core.config import settings as app_settings
from app.core.logging import get_logger
from app.financial.extraction.exceptions import (
    LLMExtractionError,
    LLMResponseError,
    LLMTransientError,
)
from app.financial.extraction.extraction_models import ChunkInput, MetricCandidate
from app.financial.metrics.metric_aliases import resolve_alias
from app.financial.metrics.normalization import normalize_currency, parse_period
from app.financial.metrics.taxonomy import MetricTaxonomy, get_metric_taxonomy

log = get_logger(__name__)

# Unit word -> (scale factor, canonical label). PERCENT handled separately.
_UNIT_SCALE = {
    "thousand": (Decimal(10) ** 3, "THOUSAND"), "thousands": (Decimal(10) ** 3, "THOUSAND"),
    "k": (Decimal(10) ** 3, "THOUSAND"),
    "million": (Decimal(10) ** 6, "MILLION"), "millions": (Decimal(10) ** 6, "MILLION"),
    "mm": (Decimal(10) ** 6, "MILLION"), "m": (Decimal(10) ** 6, "MILLION"),
    "billion": (Decimal(10) ** 9, "BILLION"), "billions": (Decimal(10) ** 9, "BILLION"),
    "bn": (Decimal(10) ** 9, "BILLION"), "b": (Decimal(10) ** 9, "BILLION"),
    "trillion": (Decimal(10) ** 12, "TRILLION"), "tn": (Decimal(10) ** 12, "TRILLION"),
}

_RESPONSE_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "metric_name": {"type": "STRING"},
            "value": {"type": "NUMBER"},
            "currency": {"type": "STRING"},
            "unit": {"type": "STRING"},
            "period": {"type": "STRING"},
            "confidence": {"type": "NUMBER"},
        },
        "required": ["metric_name", "value", "unit"],
    },
}


class LLMExtractor:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        taxonomy: MetricTaxonomy | None = None,
        max_retries: int = 3,
        base_delay: float = 2.0,
        timeout: float = 60.0,
        client: object | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self.tax = taxonomy or get_metric_taxonomy()
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._timeout = timeout
        self._client = client
        self._sleep = sleep

    @classmethod
    def from_settings(cls, *, client: object | None = None) -> LLMExtractor:
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

    def extract(self, chunks: list[ChunkInput]) -> list[MetricCandidate]:
        if not self.enabled:
            log.warning("extraction.llm_disabled", reason="no GEMINI_API_KEY; rule-only")
            return []
        out: list[MetricCandidate] = []
        for ch in chunks:
            try:
                raw = self._with_retries(lambda text=ch.text: self._generate(text))
                out.extend(self._parse(raw, ch))
            except LLMExtractionError as exc:
                log.error("extraction.llm_chunk_failed", chunk_id=ch.chunk_id, error=str(exc))
                # degrade: skip this chunk's LLM contribution, keep going
        return out

    # ---- network (overridden in tests) --------------------------------------

    def _build_prompt(self, text: str) -> str:
        canonicals = ", ".join(self.tax.canonicals())
        return (
            "Extract financial metrics EXPLICITLY stated in the text below. "
            "Only include metrics from this set (use the canonical name): "
            f"{canonicals}.\n"
            "Return the number exactly as written (do NOT scale it), with its unit "
            "(e.g. million, billion, percent) and currency if shown, the period if "
            "stated, and your confidence 0-1. Do NOT infer, compute, or estimate "
            "values — only extract what is literally present.\n\n"
            f"TEXT:\n{text}"
        )

    def _get_client(self) -> object:
        if self._client is None:
            from google import genai  # lazy import

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _generate(self, text: str) -> str:
        from google.genai import types  # lazy import

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
        except Exception as exc:  # noqa: BLE001 - classify
            raise self._classify(exc) from exc
        return resp.text or "[]"

    def _with_retries(self, call: Callable[[], str]) -> str:
        attempt = 0
        while True:
            try:
                return call()
            except LLMExtractionError as exc:
                if not getattr(exc, "retryable", False) or attempt >= self._max_retries:
                    raise
                delay = self._base_delay * (2 ** attempt)
                attempt += 1
                log.warning("extraction.llm_retry", attempt=attempt, error=str(exc))
                self._sleep(delay)

    @staticmethod
    def _classify(exc: Exception) -> LLMExtractionError:
        msg = str(exc).lower()
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        if code == 429 or "rate limit" in msg or "resource_exhausted" in msg or "quota" in msg:
            return LLMTransientError(str(exc))
        if (isinstance(code, int) and code >= 500) or "timeout" in msg or "unavailable" in msg:
            return LLMTransientError(str(exc))
        return LLMExtractionError(str(exc))

    # ---- parsing (deterministic) --------------------------------------------

    def _parse(self, raw: str, ch: ChunkInput) -> list[MetricCandidate]:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(f"invalid JSON from LLM: {exc}") from exc
        if not isinstance(items, list):
            raise LLMResponseError("LLM response is not a JSON array")

        out: list[MetricCandidate] = []
        for item in items:
            cand = self._to_candidate(item, ch)
            if cand is not None:
                out.append(cand)
        return out

    def _to_candidate(self, item: dict, ch: ChunkInput) -> MetricCandidate | None:
        if not isinstance(item, dict):
            return None
        name = str(item.get("metric_name", "")).strip()
        canonical = name if self.tax.get(name) else resolve_alias(name, taxonomy=self.tax)
        if not canonical:
            return None
        definition = self.tax.get(canonical)
        if definition is None:
            return None

        try:
            number = Decimal(str(item["value"]))
        except (InvalidOperation, KeyError, TypeError):
            return None

        value, unit = self._normalize(number, str(item.get("unit", "")), definition.value_kind)
        currency = None if definition.value_kind == "percent" else normalize_currency(
            item.get("currency")
        )
        year, quarter = parse_period(item.get("period"))
        year = year if year is not None else ch.fiscal_year
        quarter = quarter if quarter is not None else ch.fiscal_quarter

        section_match = ch.normalized_section_name in definition.expected_sections
        try:
            raw_conf = float(item.get("confidence", 0.7))
        except (TypeError, ValueError):
            raw_conf = 0.7
        return MetricCandidate(
            normalized_metric_name=canonical,
            metric_name=name or canonical,
            category=definition.category,
            value=value,
            currency=currency,
            unit=unit,
            fiscal_year=year,
            fiscal_quarter=quarter,
            source_chunk_id=ch.chunk_id,
            source_text=(ch.text or "")[:300].strip(),
            method="LLM_BASED",
            raw_confidence=max(0.0, min(1.0, raw_conf)),
            has_currency_or_scale=bool(currency) or unit not in ("ABSOLUTE",),
            section_match=section_match,
        )

    @staticmethod
    def _normalize(number: Decimal, unit_word: str, value_kind: str) -> tuple[Decimal, str]:
        u = unit_word.strip().lower().rstrip(".")
        if value_kind == "percent" or u in ("%", "percent", "pct"):
            return number, "PERCENT"
        if u in _UNIT_SCALE:
            factor, label = _UNIT_SCALE[u]
            return number * factor, label
        return number, "ABSOLUTE"
