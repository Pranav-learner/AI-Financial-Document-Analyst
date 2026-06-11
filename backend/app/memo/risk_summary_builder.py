"""Risk summary section builder for Phase 9: Investment Memo."""

from __future__ import annotations

from app.memo.memo_models import MemoPackage


class RiskSummaryBuilder:
    """Builds prompt context and fallback template for Risk Summary section."""

    def build_context_prompt(self, package: MemoPackage) -> str:
        """Structures risks and severity levels for the prompt."""
        risks_text = "\n".join(
            [f"- [Risk {r.id}] Category: {r.category}, Severity: {r.severity}, Description: {r.description}"
             for r in package.risks]
        )
        return f"Risk Intelligence:\n{risks_text or 'No risk factor intelligence detected.'}\n"

    def generate_fallback(self, package: MemoPackage) -> str:
        """Returns a deterministic fallback narrative summarizing risk profiles."""
        if not package.risks:
            return "No risk factors were identified for this company."
        
        # Sort by severity
        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_risks = sorted(package.risks, key=lambda x: severity_rank.get(x.severity, 4))
        
        narrative = f"A risk profile assessment for {package.company_name} identified {len(package.risks)} key risk areas. "
        top_risks = [f"{r.category} ({r.severity} severity: {r.description})" for r in sorted_risks[:3]]
        narrative += "Top concerns include: " + "; ".join(top_risks) + "."
        return narrative
