"""Benchmark summary section builder for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class BenchmarkSummaryBuilder:
    """Builds prompt context and fallback template for Benchmark Comparison section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures cohort benchmarking metrics for the prompt."""
        if not package.benchmark:
            return "No peer group cohort benchmarking data has been run or supplied for this memo."

        b = package.benchmark
        return (
            f"Cohort Benchmarking Scores:\n"
            f"- Overall score: {b.overall_score:.1f} (Cohort Rank: {b.rank})\n"
            f"- Financial score: {b.financial_score:.1f}\n"
            f"- Risk score: {b.risk_score:.1f}\n"
            f"- Tone score: {b.tone_score:.1f}\n"
            f"- Capital allocation score: {b.capital_allocation_score:.1f}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative summarizing benchmarking ranks."""
        if not package.benchmark:
            return "Benchmark comparison data was not supplied for this report."

        b = package.benchmark
        return (
            f"Compared to its peer cohort, {package.company_name} ranked {b.rank} overall with a score of "
            f"{b.overall_score:.1f}/100. Relational dimension performance breakdown: "
            f"Financial performance scored {b.financial_score:.1f}, risk metrics scored {b.risk_score:.1f}, "
            f"management commentary tone scored {b.tone_score:.1f}, and capital allocation scored "
            f"{b.capital_allocation_score:.1f}."
        )
