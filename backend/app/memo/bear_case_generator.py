"""Bear case section generator for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class BearCaseGenerator:
    """Builds prompt context and fallback template for Bear Case section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures high-severity risks, negative comparison metrics, and weak tone for the prompt."""
        critical_risks = [r for r in package.risks if r.severity in ("CRITICAL", "HIGH")]
        negative_comparisons = [c for c in package.comparisons if c.change_pct and c.change_pct < 0]
        
        risks_text = "\n".join([f"- High Risk: {r.category} ({r.description})" for r in critical_risks[:3]])
        comps_text = "\n".join([f"- Declining performance: {c.metric_name} fell by {c.change_pct}%" for c in negative_comparisons[:3]])
        
        return (
            f"Bearish indicators:\n"
            f"Critical Risk Areas:\n{risks_text or 'None'}\n"
            f"Performance Declines:\n{comps_text or 'None'}\n"
        )

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative for the Bear Case."""
        narrative = f"The bear case for {package.company_name} is centered on documented vulnerabilities: "
        concerns = []
        for r in package.risks:
            if r.severity in ("CRITICAL", "HIGH"):
                concerns.append(f"{r.category} risk ({r.description[:50]}...)")
        for c in package.comparisons:
            if c.change_pct and c.change_pct < 0:
                concerns.append(f"decline in {c.metric_name} ({c.change_pct:.1f}%)")
        
        if concerns:
            narrative += "Key vulnerabilities include " + ", ".join(concerns[:3]) + "."
        else:
            narrative += "No critical risks or negative comparisons were deterministically highlighted."
        return narrative
