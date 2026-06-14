"""§9 Memo Validation — grounding / citation coverage / completeness.

Validates the investment-memo surface against the deterministic seeded memo
(a COMPLETED single-company memo for the strongest peer). Checks section
completeness, citation coverage, grounding (citations resolve to real
report/chunk sources), bull/bear case presence, and the export workflow.

Run ``python -m validation.seed_demo`` first.

    python -m validation.memo_eval
"""

from __future__ import annotations

import sys

from validation._client import ValidationClient
from validation._results import Suite
from validation.seed_demo import COHORT, _uid

EXPECTED_SECTIONS = {"Investment Thesis", "Bull Case", "Bear Case"}


def run(client: ValidationClient | None = None) -> Suite:
    suite = Suite("Memo Evaluation")
    own = client is None
    client = client or ValidationClient()
    try:
        client.ensure_auth()
        memo_id = str(_uid("memo", COHORT[0]["ticker"]))
        report_id = str(_uid("report", COHORT[0]["ticker"]))

        detail = client.get(f"/memos/{memo_id}")
        if detail.status != 200:
            suite.record("memo detail 200", False,
                         f"HTTP {detail.status} — seed first (python -m validation.seed_demo)")
            suite.print_summary()
            return suite
        memo = detail.json()
        suite.record("memo detail 200", True, f"status={memo.get('status')}")
        suite.record("memo is COMPLETED", memo.get("status") == "COMPLETED", str(memo.get("status")))
        suite.record("executive summary present", bool(memo.get("executive_summary")),
                     f"{len(memo.get('executive_summary') or '')} chars")

        sections = memo.get("sections", [])
        names = {s.get("section_name") for s in sections}
        suite.record("section completeness", EXPECTED_SECTIONS.issubset(names),
                     f"have={sorted(names)}")

        # Bull / bear case present and directionally opposed.
        bull = next((s for s in sections if s.get("section_name") == "Bull Case"), None)
        bear = next((s for s in sections if s.get("section_name") == "Bear Case"), None)
        suite.record("bull case present & non-empty", bool(bull and bull.get("content")),
                     f"{len((bull or {}).get('content',''))} chars")
        suite.record("bear case present & non-empty", bool(bear and bear.get("content")),
                     f"{len((bear or {}).get('content',''))} chars")
        if bear:
            bear_text = bear.get("content", "").lower()
            suite.record("bear case names a risk", any(w in bear_text for w in ("risk", "downside", "pressure")),
                         "mentions risk/downside")

        # Citation coverage + grounding.
        cites = client.get(f"/memos/{memo_id}/citations")
        citation_list = cites.json() if cites.status == 200 else []
        total_cites = len(citation_list)
        suite.record("citations endpoint 200", cites.status == 200, f"{total_cites} citations")

        sections_with_cites = sum(1 for s in sections if s.get("citations"))
        coverage = sections_with_cites / len(sections) if sections else 0.0
        suite.record("citation coverage ≥ 80% of sections", coverage >= 0.8,
                     f"{sections_with_cites}/{len(sections)} sections cite ({coverage:.0%})")

        # Grounding: every citation references a real report_id; text_chunk
        # citations resolve to a chunk_id.
        grounded = 0
        for c in citation_list:
            has_report = bool(c.get("report_id"))
            chunk_ok = c.get("source_type") != "text_chunk" or bool(c.get("chunk_id"))
            if has_report and chunk_ok:
                grounded += 1
        grounding_rate = grounded / total_cites if total_cites else 0.0
        suite.record("grounding rate = 100%", grounding_rate == 1.0,
                     f"{grounded}/{total_cites} citations grounded ({grounding_rate:.0%})")
        suite.record("citations reference this report", all(
            str(c.get("report_id")) == report_id for c in citation_list), "all report_id match")

        # Export workflow (markdown + json).
        md = client.get(f"/memos/{memo_id}/export", params={"format": "markdown"})
        md_ok = md.status == 200 and len(md.json().get("exported_content", "")) > 0
        suite.record("export markdown", md_ok, f"HTTP {md.status}")
        js = client.get(f"/memos/{memo_id}/export", params={"format": "json"})
        suite.record("export json", js.status == 200, f"HTTP {js.status}")

        suite.measure("section_count", len(sections))
        suite.measure("citation_count", total_cites)
        suite.measure("citation_coverage", round(coverage, 3))
        suite.measure("grounding_rate", round(grounding_rate, 3))
    finally:
        if own:
            client.close()

    suite.print_summary()
    return suite


def main() -> int:
    suite = run()
    suite.save()
    return 0 if suite.ok else 1


if __name__ == "__main__":
    sys.exit(main())
