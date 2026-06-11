"""Metric-extraction evaluation (Phase 3A, task §13).

Measures extraction quality against a reusable gold dataset (configurable via
`METRIC_GOLD_PATH`). Metrics:

  * **extraction_accuracy** (recall): expected metrics correctly extracted (right
    canonical name AND value within tolerance) / total expected.
  * **precision**: correct extractions / total extracted.
  * **normalization_accuracy**: of name-matched metrics, fraction whose normalized
    absolute value matches the gold value within tolerance (did normalization work?).
  * **validation_failure_rate**: candidates dropped by deterministic validation.
  * **rule_vs_llm_agreement**: agreement rate when an LLM extractor is provided
    (n/a / 0 in rule-only mode).

Deterministic (rule + normalization). LLM agreement is optional and only computed
when an LLM extractor is injected.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from app.core.config import settings
from app.financial.extraction.extraction_models import ChunkInput
from app.financial.extraction.hybrid_extractor import HybridExtractor
from app.financial.extraction.llm_extractor import LLMExtractor
from app.financial.extraction.rule_extractor import RuleBasedExtractor
from app.financial.extraction.validators import MetricValidator

_DEFAULT_PATH = Path(__file__).with_name("gold_dataset.json")
_REL_TOL = Decimal("0.01")


@dataclass
class GoldExample:
    id: str
    text: str
    section: str | None
    fiscal_year: int | None
    expected: list[dict]


@dataclass
class ExtractionEvaluationReport:
    num_examples: int
    total_expected: int
    total_extracted: int
    correct: int
    extraction_accuracy: float          # recall
    precision: float
    normalization_accuracy: float
    validation_failure_rate: float
    rule_vs_llm_agreement: float
    per_metric: dict[str, dict] = field(default_factory=dict)

    def as_dict(self) -> dict:
        from dataclasses import asdict

        return asdict(self)


def load_gold_dataset(path: str | Path | None = None) -> list[GoldExample]:
    p = Path(path) if path else (
        Path(settings.metric_gold_path) if settings.metric_gold_path else _DEFAULT_PATH
    )
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


def _values_match(a: Decimal, b: Decimal) -> bool:
    if a == b:
        return True
    m = max(abs(a), abs(b))
    return m > 0 and abs(a - b) <= _REL_TOL * m


class ExtractionEvaluator:
    def __init__(
        self,
        *,
        rule_extractor: RuleBasedExtractor | None = None,
        llm_extractor: LLMExtractor | None = None,
        validator: MetricValidator | None = None,
    ) -> None:
        self.rule = rule_extractor or RuleBasedExtractor()
        self.llm = llm_extractor
        self.validator = validator or MetricValidator()

    def evaluate(self, examples: list[GoldExample]) -> ExtractionEvaluationReport:
        total_expected = total_extracted = correct = name_matched = norm_correct = 0
        validation_failures = validation_total = 0
        agreements = disagreements = 0
        per_metric: dict[str, dict] = {}

        # Optional hybrid run for rule-vs-LLM agreement.
        hybrid = (
            HybridExtractor(rule_extractor=self.rule, llm_extractor=self.llm, validator=self.validator)
            if self.llm is not None and self.llm.enabled
            else None
        )

        for ex in examples:
            chunk = ChunkInput(
                chunk_id=ex.id, text=ex.text, normalized_section_name=ex.section,
                fiscal_year=ex.fiscal_year, fiscal_quarter=None,
            )
            candidates = self.rule.extract([chunk])
            validation_total += len(candidates)
            valid = []
            for c in candidates:
                if self.validator.validate(c).is_valid:
                    valid.append(c)
                else:
                    validation_failures += 1

            by_name = {c.normalized_metric_name: c for c in valid}
            total_extracted += len(valid)

            for exp in ex.expected:
                total_expected += 1
                name = exp["metric"]
                stats = per_metric.setdefault(name, {"expected": 0, "correct": 0})
                stats["expected"] += 1
                got = by_name.get(name)
                if got is None:
                    continue
                name_matched += 1
                if _values_match(Decimal(str(got.value)), Decimal(str(exp["value"]))):
                    correct += 1
                    norm_correct += 1
                    stats["correct"] += 1

            if hybrid is not None:
                run = hybrid.extract([chunk])
                agreements += run.stats.agreements
                disagreements += run.stats.disagreements

        agree_total = agreements + disagreements
        return ExtractionEvaluationReport(
            num_examples=len(examples),
            total_expected=total_expected,
            total_extracted=total_extracted,
            correct=correct,
            extraction_accuracy=round(correct / total_expected, 4) if total_expected else 0.0,
            precision=round(correct / total_extracted, 4) if total_extracted else 0.0,
            normalization_accuracy=round(norm_correct / name_matched, 4) if name_matched else 0.0,
            validation_failure_rate=round(validation_failures / validation_total, 4) if validation_total else 0.0,
            rule_vs_llm_agreement=round(agreements / agree_total, 4) if agree_total else 0.0,
            per_metric=per_metric,
        )
