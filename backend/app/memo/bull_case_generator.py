"""Bull case section generator for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class BullCaseGenerator:
    """Builds prompt context and fallback template for Bull Case section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures high-performance metrics, positive tone, and benchmark wins for the prompt."""
        positive_metrics = [m for m in package.financial_metrics if m.category in ("REVENUE", "PROFITABILITY") and m.value and m.value > 0]
        positive_comparisons = [c for c in package.comparisons if c.change_pct and c.change_pct > 0]
        positive_analytics = [a for a in package.analytics if a.score and a.score > 50]
        
        metrics_text = "\n".join([f"- Positive metric: {m.name} = {m.value} {m.unit}" for m in positive_metrics[:3]])
        comps_text = "\n".join([f"- Growth metric: {c.metric_name} grew by {c.change_pct}%" for c in positive_comparisons[:3]])
        analytics_text = "\n".join([f"- Analytic strength: {a.signal_type} ({a.explanation})" for a in positive_analytics[:3]])
        
        return (
            f"Bullish indicators:\n"
            f"Positive Financials:\n{metrics_text or 'None'}\n"
            f"Favourable Comparisons:\n{comps_text or 'None'}\n"
            f"Positive Ratios/Signals:\n{analytics_text or 'None'}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative for the Bull Case."""
        narrative = f"The bull case for {package.company_name} is supported by key operational signals: "
        indicators = []
        for c in package.comparisons:
            if c.change_pct and c.change_pct > 0:
                indicators.append(f"growth in {c.metric_name} ({c.change_pct:+.1f}%)")
        if package.benchmark and package.benchmark.rank and package.benchmark.rank <= 3:
            indicators.append(f"top-tier ranking ({package.benchmark.rank}) within peer benchmarking cohort")
        
        if indicators:
            narrative += "Indicators include " + ", ".join(indicators[:3]) + "."
        else:
            narrative += "No significant positive growth comparisons were deterministically verified."
        return narrative
