"""Master orchestrator for the Phase 12 validation suite.

Seeds the demo dataset (unless --no-seed) and runs every validation suite
against the live backend using a single shared, authenticated client, then
writes a combined JSON report and prints a final readiness summary.

    python -m validation.run_all                 # full suite
    python -m validation.run_all --no-seed        # skip re-seeding
    python -m validation.run_all --fast           # skip load + agent (LLM) suites
"""

from __future__ import annotations

import json
import sys
import time

from validation import (
    agent_eval,
    benchmark_eval,
    deployment_audit,
    e2e_validation,
    load_test,
    memo_eval,
    performance_benchmark,
    retrieval_eval,
    security_audit,
    smoke_test,
)
from validation._client import ValidationClient
from validation._results import REPORTS_DIR, Suite, bold, green, red, yellow


def main() -> int:
    argv = set(sys.argv[1:])
    do_seed = "--no-seed" not in argv
    fast = "--fast" in argv

    print(bold("\n=== Phase 12 — Competition Readiness Validation ===\n"))

    if do_seed:
        print("Seeding demo dataset…")
        try:
            import asyncio

            from validation.seed_demo import seed
            res = asyncio.run(seed())
            print(f"  seeded {len(res['companies'])} companies, {res['chunks']} chunks, "
                  f"{res['metrics']} metrics, {res['risks']} risks, {res['tone']} tone rows\n")
        except Exception as exc:  # noqa: BLE001
            print(red(f"  seed failed: {exc}\n"))

    client = ValidationClient()
    try:
        client.ensure_auth()
    except Exception as exc:  # noqa: BLE001
        print(red(f"Cannot authenticate against {client.base_url}: {exc}"))
        print("Is the backend running? (docker compose up)  Schema migrated? (alembic upgrade head)")
        return 2

    # Deployment audit is static (no client needed); the rest share the client.
    suites: list[Suite] = []
    runners = [
        ("Deployment Audit", lambda: deployment_audit.run()),
        ("Smoke Test", lambda: smoke_test.run(client)),
        ("E2E Validation", lambda: e2e_validation.run(client)),
        ("Performance Benchmark", lambda: performance_benchmark.run(client, iterations=20)),
        ("Retrieval Evaluation", lambda: retrieval_eval.run(client)),
        ("Memo Evaluation", lambda: memo_eval.run(client)),
        ("Benchmark Evaluation", lambda: benchmark_eval.run(client)),
        ("Security Audit", lambda: security_audit.run(client)),
    ]
    if not fast:
        runners.append(("Load Test", lambda: load_test.run(client, concurrency=10, total=60)))
        runners.append(("Agent Evaluation", lambda: agent_eval.run(client)))

    started = time.time()
    for name, fn in runners:
        print(bold(f"\n──── {name} ────"))
        try:
            suites.append(fn())
        except Exception as exc:  # noqa: BLE001
            s = Suite(name)
            s.record("suite executed", False, f"crashed: {exc}")
            s.print_summary()
            suites.append(s)
    # Security audit trips the login rate-limiter; run it last among client suites
    # is already handled by ordering above (it is near the end).

    # ---- combined report --------------------------------------------------
    total_pass = sum(s.passed for s in suites)
    total_fail = sum(s.failed for s in suites)
    total_warn = sum(s.warned for s in suites)
    overall_ok = total_fail == 0

    combined = {
        "phase": "12",
        "overall_ok": overall_ok,
        "duration_s": round(time.time() - started, 1),
        "totals": {"passed": total_pass, "failed": total_fail, "warned": total_warn},
        "suites": [s.to_dict() for s in suites],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "run_all.json").write_text(json.dumps(combined, indent=2, default=str))

    print(bold("\n\n=== FINAL READINESS SUMMARY ===\n"))
    for s in suites:
        mark = green("OK   ") if s.ok else red("FAIL ")
        warn = f"  {yellow(str(s.warned)+' warn')}" if s.warned else ""
        print(f"  {mark} {s.name:24s} {s.passed:3d} passed, {s.failed} failed{warn}")
    verdict = green("COMPETITION READY") if overall_ok else red("NOT READY — see failures above")
    print(bold(f"\n  {total_pass} passed · {total_fail} failed · {total_warn} warnings"))
    print(bold(f"  Verdict: {verdict}"))
    print(f"\n  Combined report: {REPORTS_DIR / 'run_all.json'}\n")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
