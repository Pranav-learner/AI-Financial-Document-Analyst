"""§2 Competition Smoke Tests — single-command validation.

Fast, read-mostly checks that every major subsystem of a *running* backend is
reachable and well-formed. Designed to be the first thing run before a demo:

    python -m validation.smoke_test

Exit code 0 ⇒ all critical checks passed. Non-zero ⇒ at least one failed.
Assumes the demo dataset is seeded (run ``python -m validation.seed_demo``);
data-dependent checks degrade to warnings when no data is present.
"""

from __future__ import annotations

import sys

from validation._client import ValidationClient
from validation._results import Suite


def run(client: ValidationClient | None = None) -> Suite:
    suite = Suite("Smoke Test")
    own = client is None
    client = client or ValidationClient()
    try:
        # 1. Liveness / readiness (unauthenticated operational endpoints).
        h = client.get("/health", auth=False)
        suite.record("health endpoint 200", h.status == 200, f"HTTP {h.status} in {h.ms:.0f}ms")

        r = client.get("/ready", auth=False)
        ready_ok = r.status == 200
        checks = r.json().get("checks", {}) if ready_ok else {}
        suite.record(
            "readiness probe 200",
            ready_ok,
            ", ".join(f"{k}={v}" for k, v in checks.items()) or f"HTTP {r.status}",
        )
        for dep in ("database", "redis", "celery", "storage"):
            if dep in checks:
                suite.record(f"dependency {dep} ok", checks[dep] == "ok", checks[dep])

        # 2. OpenAPI surface present.
        o = client.get("/api/v1/../../openapi.json", auth=False)
        o = client.get("/openapi.json", auth=False) if o.status != 200 else o
        paths = len(o.json().get("paths", {})) if o.status == 200 else 0
        suite.record("openapi served", o.status == 200 and paths > 50, f"{paths} paths")

        # 3. Auth bootstrap (register + login).
        try:
            token = client.ensure_auth()
            suite.record("auth: register+login", bool(token), f"token len {len(token or '')}")
        except Exception as exc:  # noqa: BLE001
            suite.record("auth: register+login", False, str(exc))
            suite.print_summary()
            return suite

        me = client.get("/auth/me")
        suite.record("auth: /me returns identity", me.status == 200 and "email" in me.json(),
                     f"HTTP {me.status}")

        # 4. Auth gating: protected endpoint rejects anonymous callers.
        anon = client.get("/reports", auth=False)
        suite.record("auth gating: 401 without token", anon.status == 401, f"HTTP {anon.status}")

        # 5. Reports list (authed).
        rep = client.get("/reports")
        total = rep.json().get("total", 0) if rep.status == 200 else 0
        suite.record("reports list 200", rep.status == 200, f"HTTP {rep.status}, total={total}")
        has_data = total > 0
        suite.record("demo data present", has_data,
                     "seed with `python -m validation.seed_demo`" if not has_data else f"{total} reports",
                     warn=not has_data)

        # 6. Data-dependent reads (only if seeded).
        if has_data:
            report = rep.json()["items"][0]
            report_id = report["id"]
            for label, path in (
                ("report risks", f"/reports/{report_id}/risks"),
                ("report tone", f"/reports/{report_id}/tone"),
                ("report metrics", f"/reports/{report_id}/metrics"),
                ("report sections", f"/reports/{report_id}/sections"),
                ("report chunks", f"/reports/{report_id}/chunks"),
            ):
                resp = client.get(path)
                suite.record(f"read {label}", resp.status == 200, f"HTTP {resp.status} in {resp.ms:.0f}ms")

            # 7. Hybrid retrieval.
            hb = client.post("/search/hybrid", json={"query": "revenue and free cash flow", "top_k": 5})
            suite.record("hybrid search 200", hb.status == 200, f"HTTP {hb.status} in {hb.ms:.0f}ms")

            # 8. Retrieval evaluation harness reachable.
            ev = client.get("/evaluation/benchmarks")
            suite.record("evaluation benchmarks listed", ev.status == 200, f"HTTP {ev.status}")

        suite.measure("data_seeded", has_data)
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
