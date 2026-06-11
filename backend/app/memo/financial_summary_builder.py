"""Financial summary section builder for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class FinancialSummaryBuilder:
    """Builds prompt context and fallback template for Financial Summary section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures financial metrics, comparisons, and ratios for the prompt."""
        metrics_text = "\n".join(
            [f"- {m.name}: {m.value} {m.unit} ({m.period})" for m in package.financial_metrics]
        )
        comparisons_text = "\n".join(
            [f"- {c.metric_name} ({c.comparison_type}): current {c.current_value}, previous {c.previous_value}, change {c.change_pct}%"
             for c in package.comparisons]
        )
        analytics_text = "\n".join(
            [f"- {a.signal_type} trend for {a.metric_name}: score {a.score}, explanation: {a.explanation}"
             for a in package.analytics]
        )
        return (
            f"Financial Metrics:\n{metrics_text or 'None'}\n\n"
            f"Period-over-Period Comparisons:\n{comparisons_text or 'None'}\n\n"
            f"Financial Analytics & Ratios:\n{analytics_text or 'None'}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative summarizing metrics."""
        if not package.financial_metrics:
            return "No financial metrics were extracted for this period."
        
        narrative = f"Financial performance analysis for {package.company_name} indicates the following metrics: "
        parts = []
        for m in package.financial_metrics[:5]:
            val_str = f"{m.value:.2f}" if m.value is not None else "N/A"
            unit_str = f" {m.unit}" if m.unit else ""
            parts.append(f"{m.name} of {val_str}{unit_str}")
        narrative += ", ".join(parts) + "."

        if package.comparisons:
            narrative += " Period-over-period comparisons show: "
            comp_parts = []
            for c in package.comparisons[:3]:
                pct_str = f"{c.change_pct:+.1f}%" if c.change_pct is not None else "N/A"
                comp_parts.append(f"{c.metric_name} changed by {pct_str} ({c.comparison_type})")
            narrative += ", ".join(comp_parts) + "."

        return narrative
