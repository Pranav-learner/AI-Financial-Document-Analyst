"""Risk-extraction evaluation (Phase 4).

Measures extraction quality against a reusable gold dataset.
Metrics:
  * recall (extraction_accuracy): expected risks matched / total expected
  * precision: correct extractions / total extracted
  * category_accuracy: correct category / matched expected
  * severity_accuracy: correct severity / matched expected
  * validation_failure_rate: validation failures / total candidate extractions
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.risk.extraction.extraction_models import RiskChunkInput
from app.risk.extraction.hybrid_extractor import HybridRiskExtractor
from app.risk.extraction.rule_extractor import RuleBasedRiskExtractor
from app.risk.extraction.llm_extractor import RiskLLMExtractor
from app.risk.extraction.validators import RiskValidator

_DEFAULT_PATH = Path(__file__).with_name("gold_dataset.json")


@dataclass
class GoldExample:
    id: str
    text: str
    section: str | None
    fiscal_year: int | None
    expected: list[dict]


@dataclass
class RiskExtractionEvaluationReport:
    num_examples: int
    total_expected: int
    total_extracted: int
    correct: int
    recall: float
    precision: float
    category_accuracy: float
    severity_accuracy: float
    validation_failure_rate: float
    rule_vs_llm_agreement: float
    per_category: dict[str, dict] = field(default_factory=dict)

    def as_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


def load_gold_dataset(path: str | Path | None = None) -> list[GoldExample]:
    p = Path(path) if path else _DEFAULT_PATH
    raw = json.loads(p.read_text(encoding="utf-8"))
    return [
        GoldExample(
            id=e["id"],
            text=e["text"],
            section=e.get("section"),
            fiscal_year=e.get("fiscal_year"),
            expected=e.get("expected", []),
        )
        for e in raw.get("examples", [])
    ]


def _stop_words_filter(name: str) -> set[str]:
    stop_words = {
        "risk", "factors", "and", "or", "the", "a", "of", "to", "in", "for",
        "on", "with", "at", "by", "from", "up", "about", "into", "over", "after",
    }
    import re
    name_clean = name.replace("_", " ")
    words = re.findall(r"\w+", name_clean.lower())
    return {w for w in words if w not in stop_words}


def calculate_jaccard(name1: str, name2: str) -> float:
    tokens1 = _stop_words_filter(name1)
    tokens2 = _stop_words_filter(name2)
    if not tokens1 or not tokens2:
        return 0.0
    union = tokens1.union(tokens2)
    intersection = tokens1.intersection(tokens2)
    return len(intersection) / len(union)


class RiskExtractionEvaluator:
    def __init__(
        self,
        *,
        rule_extractor: RuleBasedRiskExtractor | None = None,
        llm_extractor: RiskLLMExtractor | None = None,
        validator: RiskValidator | None = None,
    ) -> None:
        self.rule = rule_extractor or RuleBasedRiskExtractor()
        self.llm = llm_extractor
        self.validator = validator or RiskValidator()

    def evaluate(self, examples: list[GoldExample]) -> RiskExtractionEvaluationReport:
        total_expected = 0
        total_extracted = 0
        correct = 0
        category_correct = 0
        severity_correct = 0
        matched_count = 0
        validation_failures = 0
        validation_total = 0
        agreements = 0
        disagreements = 0
        per_category: dict[str, dict] = {}

        hybrid = (
            HybridRiskExtractor(rule_extractor=self.rule, llm_extractor=self.llm, validator=self.validator)
            if self.llm is not None and self.llm.enabled
            else None
        )

        for ex in examples:
            chunk = RiskChunkInput(
                chunk_id=ex.id,
                text=ex.text,
                normalized_section_name=ex.section,
                fiscal_year=ex.fiscal_year,
                fiscal_quarter=None,
            )

            # 1. Run rule extraction to compute validation metrics
            candidates = self.rule.extract([chunk])
            validation_total += len(candidates)
            valid = []
            for c in candidates:
                if self.validator.validate(c).is_valid:
                    valid.append(c)
                else:
                    validation_failures += 1

            total_extracted += len(valid)

            # 2. Check overlap between expected and valid
            for exp in ex.expected:
                total_expected += 1
                cat = exp["category"]
                stats = per_category.setdefault(cat, {"expected": 0, "correct": 0})
                stats["expected"] += 1

                # Find matching extracted candidate by name token similarity
                best_match = None
                best_sim = 0.0
                for v in valid:
                    sim = calculate_jaccard(v.normalized_risk_name, exp["normalized_risk_name"])
                    if sim >= 0.4 and sim > best_sim:
                        best_match = v
                        best_sim = sim

                if best_match is not None:
                    matched_count += 1
                    is_correct = True
                    if best_match.category == exp["category"]:
                        category_correct += 1
                    else:
                        is_correct = False

                    if best_match.severity == exp["severity"]:
                        severity_correct += 1
                    else:
                        is_correct = False

                    if is_correct:
                        correct += 1
                        stats["correct"] += 1

            # 3. Agreement metric if hybrid is active
            if hybrid is not None:
                run = hybrid.extract([chunk])
                agreements += run.stats.agreements
                disagreements += run.stats.disagreements

        agree_total = agreements + disagreements
        return RiskExtractionEvaluationReport(
            num_examples=len(examples),
            total_expected=total_expected,
            total_extracted=total_extracted,
            correct=correct,
            recall=round(correct / total_expected, 4) if total_expected else 0.0,
            precision=round(correct / total_extracted, 4) if total_extracted else 0.0,
            category_accuracy=round(category_correct / matched_count, 4) if matched_count else 0.0,
            severity_accuracy=round(severity_correct / matched_count, 4) if matched_count else 0.0,
            validation_failure_rate=round(validation_failures / validation_total, 4) if validation_total else 0.0,
            rule_vs_llm_agreement=round(agreements / agree_total, 4) if agree_total else 0.0,
            per_category=per_category,
        )
