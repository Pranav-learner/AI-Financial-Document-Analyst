"""Post-generation validator for Phase 9: Investment Memo."""

from __future__ import annotations

import re
from app.memo.exceptions import MemoValidationError
from app.memo.memo_models import MemoPackage, MemoSectionSchema


class MemoValidator:
    """Enforces grounding, verification, and negative constraints on the generated memo."""

    PROHIBITED_TERMS = [
        r"\bstrong buy\b",
        r"\bstrong sell\b",
        r"\bbuy recommendation\b",
        r"\bsell recommendation\b",
        r"\bprice target\b",
        r"\btarget price\b",
        r"\bportfolio allocation\b",
        r"\bportfolio optimization\b",
        r"\bstock rating\b",
        r"\binvestment advice\b",
    ]

    def validate(self, package: MemoPackage, executive_summary: str, sections: list[MemoSectionSchema]) -> None:
        """Validates the entire generated content against security and grounding rules."""
        
        # 1. Negative constraints check
        all_text = executive_summary + "\n" + "\n".join([s.content for s in sections])
        all_text_lower = all_text.lower()

        for term in self.PROHIBITED_TERMS:
            if re.search(term, all_text_lower):
                raise MemoValidationError(
                    f"Generated memo violates negative constraints: found prohibited term/pattern matching '{term}'"
                )

        # Let's check for direct buy/sell ratings like rating: buy or buy rating
        if re.search(r"\brating\b\s*:\s*\b(buy|sell|hold)\b", all_text_lower):
            raise MemoValidationError(
                "Generated memo violates negative constraints: found direct rating recommendation."
            )

        # 2. Grounding check: Extract numbers and verify they exist in the package
        self._verify_numerical_grounding(package, all_text)

    def _verify_numerical_grounding(self, package: MemoPackage, text: str) -> None:
        """Extracts numbers from text and verifies they are grounded in the package."""
        # Find all numbers (like 96.7, -12, 100, 2026, 45,000, 25%)
        # Exclude common structural or formatting numbers (e.g. section numbers 1, 2, 3, bullet counts, short index/dates)
        found_numbers = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?%?\b", text)
        
        # Build a set of allowed numbers from package
        allowed = set()
        
        # Add metadata numbers
        if package.reporting_year:
            allowed.add(str(package.reporting_year))
            allowed.add(str(package.reporting_year - 1))
            allowed.add(str(package.reporting_year + 1))
            allowed.add(str(package.reporting_year)[2:])  # e.g., '24' for 2024
        
        # Add metric values (integer and float strings, with and without percentages)
        for m in package.financial_metrics:
            if m.value is not None:
                self._add_formatted_numbers(allowed, m.value)
        
        for c in package.comparisons:
            if c.current_value is not None:
                self._add_formatted_numbers(allowed, c.current_value)
            if c.previous_value is not None:
                self._add_formatted_numbers(allowed, c.previous_value)
            if c.change_pct is not None:
                self._add_formatted_numbers(allowed, c.change_pct)

        for a in package.analytics:
            if a.score is not None:
                self._add_formatted_numbers(allowed, a.score)
            if a.strength is not None:
                self._add_formatted_numbers(allowed, a.strength)

        for r in package.risks:
            if r.page_number is not None:
                allowed.add(str(r.page_number))

        for t in package.tones:
            self._add_formatted_numbers(allowed, t.sentiment_score)
            self._add_formatted_numbers(allowed, t.hedging_score)

        if package.benchmark:
            b = package.benchmark
            if b.overall_score is not None:
                self._add_formatted_numbers(allowed, b.overall_score)
            if b.financial_score is not None:
                self._add_formatted_numbers(allowed, b.financial_score)
            if b.risk_score is not None:
                self._add_formatted_numbers(allowed, b.risk_score)
            if b.tone_score is not None:
                self._add_formatted_numbers(allowed, b.tone_score)
            if b.capital_allocation_score is not None:
                self._add_formatted_numbers(allowed, b.capital_allocation_score)
            if b.rank is not None:
                allowed.add(str(b.rank))

        # Add document chunk page numbers
        for c in package.retrieved_evidence:
            if c.page_number is not None:
                allowed.add(str(c.page_number))

        # Add common text numbers (0-10, 100, etc.)
        for i in range(21):
            allowed.add(str(i))
            allowed.add(f"{i}.0")
        allowed.add("100")
        allowed.add("100.0")
        allowed.add("100%")

        # Validate each found number
        for num in found_numbers:
            # Strip commas and percentage signs
            clean_num = num.replace(",", "").replace("%", "")
            # Skip if it is a single digit or a small number (which are often formatting indexes)
            if clean_num.isdigit() and int(clean_num) <= 20:
                continue
            
            # Check if this exact number, or close approximation, exists in allowed set
            matched = False
            if clean_num in allowed or num in allowed:
                matched = True
            else:
                # Try float matching
                try:
                    val = float(clean_num)
                    # Check if there is an allowed value close to it
                    for allowed_val_str in allowed:
                        try:
                            allowed_val = float(allowed_val_str.replace("%", ""))
                            if abs(allowed_val - val) < 0.01:
                                matched = True
                                break
                        except ValueError:
                            continue
                except ValueError:
                    pass
            
            if not matched:
                # Allow standard years (e.g. 2020 to 2030) or common numbers to avoid false positives on dates/formatting
                try:
                    val = float(clean_num)
                    if 2010 <= val <= 2030:
                        continue
                except ValueError:
                    pass
                
                raise MemoValidationError(
                    f"Generated memo contains ungrounded figure '{num}' not found in the input sources."
                )

    def _add_formatted_numbers(self, allowed_set: set[str], value: float | int) -> None:
        """Helper to add multiple formats of a number to the allowed set."""
        val_str = str(value)
        allowed_set.add(val_str)
        allowed_set.add(f"{value:.1f}")
        allowed_set.add(f"{value:.2f}")
        allowed_set.add(f"{value:.0f}")
        allowed_set.add(f"{value:+.1f}")
        allowed_set.add(f"{value:+.2f}")
        # Percentage format
        allowed_set.add(f"{value}%")
        allowed_set.add(f"{value:.1f}%")
        allowed_set.add(f"{value:.2f}%")
        # Absolute representation if it was float-converted from integer
        if isinstance(value, float) and value.is_integer():
            allowed_set.add(str(int(value)))
