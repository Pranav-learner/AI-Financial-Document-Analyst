"""HyDE generator implementation (Phase 6)."""

from __future__ import annotations

import json
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.hyde.models import HyDEResult
from app.rag.hyde.validators import validate_hyde_document

log = get_logger(__name__)

_HYDE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "hypothetical_document": {"type": "STRING"}
    },
    "required": ["hypothetical_document"]
}


class HyDEGenerator:
    """Generates hypothetical documents using Gemini 2.5 Pro with fallback rules."""

    def __init__(self, *, client: genai.Client | None = None) -> None:
        self.api_key = settings.gemini_api_key
        self._client = client
        self.model = settings.gemini_llm_model

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(self, query: str) -> HyDEResult:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            raise ValueError("Query cannot be empty for HyDE generation")

        if self.api_key:
            try:
                prompt = (
                    "Write a short, realistic paragraph (about 3-4 sentences) answering the following financial or corporate query. "
                    "Do not include introductory words or metadata. Act as if this paragraph is a direct extract from an SEC filing (e.g. 10-K, 10-Q). "
                    "Ensure the text uses realistic professional financial/risk jargon.\n\n"
                    f"QUERY: \"{cleaned_query}\"\n"
                )

                client = self._get_client()
                resp = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=_HYDE_SCHEMA,
                        temperature=0.0
                    )
                )
                raw_text = resp.text or "{}"
                data = json.loads(raw_text)
                doc = validate_hyde_document(data["hypothetical_document"])

                return HyDEResult(
                    query=cleaned_query,
                    hypothetical_document=doc,
                    metadata={"engine": "gemini-2.5-pro"}
                )
            except Exception as exc:
                log.warning("hyde_generator.llm_failed", error=str(exc))
                # Fallback to local heuristic generation

        return self._generate_local(cleaned_query)

    def _generate_local(self, query: str) -> HyDEResult:
        # Generate realistic boilerplate corporate filing language depending on query contents
        lowered = query.lower()
        doc = ""
        if "supply chain" in lowered or "risk" in lowered or "concerns" in lowered:
            doc = (
                f"The company faces risks related to its global supply chain, including potential logistics delays, "
                f"supplier concentration, and vulnerabilities in component procurement. Disruption in manufacturing "
                f"facilities or transportation corridors could adversely impact our financial performance, operating results, "
                f"and capacity utilization."
            )
        elif "margin" in lowered or "revenue" in lowered or "profit" in lowered:
            doc = (
                f"During the reporting period, total revenues increased, driven by higher product sales and expansion "
                f"of services segments. Operating margins improved due to cost control measures and operational efficiencies, "
                f"offset by inflationary pressures and capital investments."
            )
        elif "sentiment" in lowered or "tone" in lowered or "management" in lowered:
            doc = (
                f"Management remains optimistic regarding our long-term strategic direction and commercial tailwinds. "
                f"While near-term macroeconomic headwinds and cost increases require careful capital allocation, "
                f"we continue to see strong demand and competitive advantages across our key operating segments."
            )
        else:
            doc = (
                f"Regarding the query '{query}', the company operates in a competitive environment characterized by "
                f"technological changes and evolving customer needs. We execute our business strategy to sustain growth, "
                f"improve capital efficiency, and manage potential regulatory and financial risks."
            )

        return HyDEResult(
            query=query,
            hypothetical_document=doc,
            metadata={"engine": "local_fallback"}
        )
