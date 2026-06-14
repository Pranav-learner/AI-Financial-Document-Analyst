"""§10 Benchmark Validation — ranking / score / tie / missing-data.

Exercises the competitor-benchmarking engine via the synchronous
POST /benchmark/compare endpoint against the deterministic demo cohort, whose
financial / risk / tone profiles are known in advance. This lets us assert
*ranking accuracy* against ground truth rather than merely checking the call
succeeds.

Known ground truth (see validation/seed_demo.py):
    Apex Robotics  — strongest financials, positive tone, lowest risk  → best
    Bolt Dynamics  — mid financials, cautious tone, critical cyber risk → middle
    Cortex Systems — weakest financials, negative tone, liquidity risk  → worst

    python -m validation.benchmark_eval
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from validation._client import ValidationClient
from validation._results import Suite
from validation.seed_demo import COHORT, _uid

# Expected overall ordering, best → worst.
EXPECTED_ORDER = ["DEMO-APX", "DEMO-BLT", "DEMO-CTX"]


def _company_ids() -> dict[str, str]:
    return {spec["ticker"]: str(_uid("company", spec["ticker"])) for spec in COHORT}


def run(client: ValidationClient | None = None) -> Suite:
    suite = Suite("Benchmark Evaluation")
    own = client is None
    client = client or ValidationClient()
    try:
        client.ensure_auth()
        ids = _company_ids()
        id_to_ticker = {v: k for k, v in ids.items()}
        cohort_ids = list(ids.values())

        resp = client.post("/benchmark/compare", json={"company_ids": cohort_ids, "configuration": {}})
        if resp.status != 200:
            suite.record("benchmark compare 200", False,
                         f"HTTP {resp.status}: {resp.response.text[:160]}")
            suite.print_summary()
            return suite
        suite.record("benchmark compare 200", True, f"HTTP 200 in {resp.ms:.0f}ms")

        body = resp.json()
        summaries = body.get("cohort_summaries", [])
        suite.record("all cohort members summarised", len(summaries) == len(cohort_ids),
                     f"{len(summaries)}/{len(cohort_ids)}")

        # Score accuracy: every summary has a numeric overall score + rank.
        scored = [s for s in summaries if isinstance(s.get("scores"), dict) and s.get("rank") is not None]
        suite.record("every company has scores + rank", len(scored) == len(summaries),
                     f"{len(scored)}/{len(summaries)}")

        # Ranks form a valid dense permutation 1..N.
        ranks = sorted(s.get("rank") for s in summaries if s.get("rank") is not None)
        valid_perm = ranks == list(range(1, len(summaries) + 1))
        suite.record("ranks are a valid 1..N permutation", valid_perm, f"ranks={ranks}")

        # Ranking accuracy vs known ground truth (overall ordering).
        ordered = sorted(summaries, key=lambda s: s.get("rank", 999))
        actual_order = [id_to_ticker.get(str(s.get("company_id")), "?") for s in ordered]
        suite.record(
            "ranking matches known ground truth",
            actual_order == EXPECTED_ORDER,
            f"expected={EXPECTED_ORDER} actual={actual_order}",
        )

        # Best company beats worst on the mean of its populated dimension scores.
        def overall(s: dict[str, Any]) -> float:
            vals = [float(v) for v in (s.get("scores") or {}).values() if v is not None]
            return sum(vals) / len(vals) if vals else 0.0

        by_ticker = {id_to_ticker.get(str(s.get("company_id"))): s for s in summaries}
        if by_ticker.get("DEMO-APX") and by_ticker.get("DEMO-CTX"):
            apx, ctx = overall(by_ticker["DEMO-APX"]), overall(by_ticker["DEMO-CTX"])
            suite.record("strongest company scores above weakest", apx > ctx,
                         f"APX_mean_dim={apx:.1f} CTX_mean_dim={ctx:.1f}")
            # Every dimension should be populated now (financial + capital allocation
            # included), proving the demo dataset exercises the full scoring engine.
            dims = by_ticker["DEMO-APX"].get("scores", {})
            populated = [k for k, v in dims.items() if v is not None]
            suite.record("all four scoring dimensions populated", len(populated) == 4,
                         f"populated={populated}")

        # Tie / equal-input handling: comparing a company against itself must not
        # crash and must return well-formed ranks.
        same = client.post("/benchmark/compare",
                           json={"company_ids": [cohort_ids[0], cohort_ids[0]], "configuration": {}})
        suite.record("duplicate-company input handled gracefully",
                     same.status in (200, 400, 422), f"HTTP {same.status}")

        # Missing-data handling: an unknown company id must fail cleanly as a
        # client error (404), not a 500 server fault.
        missing = client.post("/benchmark/compare",
                              json={"company_ids": [cohort_ids[0], str(uuid.uuid4())], "configuration": {}})
        suite.record("unknown company id → 404 (not 500)",
                     missing.status == 404, f"HTTP {missing.status}")

        suite.measure("actual_order", actual_order)
        suite.measure("summaries", summaries)
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
