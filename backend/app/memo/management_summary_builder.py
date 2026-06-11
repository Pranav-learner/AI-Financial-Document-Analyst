"""Management commentary summary section builder for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class ManagementSummaryBuilder:
    """Builds prompt context and fallback template for Management Commentary section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures management tone information for the prompt."""
        tone_text = "\n".join(
            [f"- Sentiment: {t.sentiment}, Confidence Level: {t.confidence_level}, Sentiment Score: {t.sentiment_score}, Hedging Score: {t.hedging_score}"
             for t in package.tones]
        )
        return f"Management Tone Analysis:\n{tone_text or 'No management tone analytics detected.'}\n"

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative summarizing management tone."""
        if not package.tones:
            return "No management commentary tone disclosures were analysed."
        
        t = package.tones[0]
        narrative = (
            f"Management commentary for {package.company_name} is characterized by an overall "
            f"{t.sentiment} sentiment and a {t.confidence_level} confidence level. "
            f"The computed sentiment score stands at {t.sentiment_score:.2f} (where higher is more positive) "
            f"with a hedging/uncertainty score of {t.hedging_score:.2f}."
        )
        return narrative
