"""Question generator section for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class QuestionGenerator:
    """Builds prompt context and fallback template for Questions to Investigate section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures unresolved anomalies, high hedging, and severe risks for follow-up questions."""
        hedged_tones = [t for t in package.tones if t.hedging_score > 0.4]
        critical_risks = [r for r in package.risks if r.severity in ("CRITICAL", "HIGH")]
        
        cautions_text = "\n".join([f"- Hedged Commentary: Sentiment={t.sentiment}, Hedging Score={t.hedging_score}" for t in hedged_tones[:2]])
        risks_text = "\n".join([f"- Risk Area: {r.category} ({r.description})" for r in critical_risks[:2]])
        
        return (
            f"Unresolved matters for due diligence:\n"
            f"Commentary with elevated hedging or uncertainty:\n{cautions_text or 'None'}\n"
            f"Vulnerable Risk exposures:\n{risks_text or 'None'}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback checklist of investigation questions."""
        questions = [
            f"1. How does management plan to mitigate the highlighted risk exposures?",
            f"2. What macro or operational drivers are causing the volatility in key metrics?"
        ]
        if package.benchmark:
            questions.append(
                f"3. What strategic changes are required to improve cohort ranking from rank {package.benchmark.rank}?"
            )
        return "\n".join(questions)
