"""§5 Performance Benchmarking — latency: avg / median / p95 / worst.

Repeatedly exercises representative read/compute endpoints on a running backend
and reports per-endpoint latency distributions. Pure measurement — no asserts on
absolute numbers (hardware-dependent); it records them and flags only gross
regressions (p95 over a generous ceiling) as warnings.

    python -m validation.performance_benchmark [iterations]
"""

from __future__ import annotations

import sys
from typing import Any

from validation._client import ValidationClient
from validation._results import Suite, latency_stats

# Generous p95 ceilings (ms) — exceeding these is a *warning*, not a failure,
# since the suite targets a dev box. Tune per environment.
CEILINGS_MS = {
    "health": 150,
    "reports_list": 400,
    "report_risks": 400,
    "report_tone": 400,
    "report_metrics": 500,
    "hybrid_search": 1500,
    "vector_search": 1500,
    "company_risk_summary": 600,
}


def _bench(client: ValidationClient, method: str, path: str, n: int, **kw: Any) -> list[float]:
    samples: list[float] = []
    for _ in range(n):
        t = client.request(method, path, **kw)
        # Only time successful calls; record status of first failure.
        samples.append(t.ms)
        if t.status >= 500:
            break
    return samples


def run(client: ValidationClient | None = None, iterations: int = 20) -> Suite:
    suite = Suite("Performance Benchmark")
    own = client is None
    client = client or ValidationClient()
    try:
        client.ensure_auth()
        rep = client.get("/reports")
        items = rep.json().get("items", []) if rep.status == 200 else []
        report_id = items[0]["id"] if items else None
        company_id = items[0].get("company_id") if items else None

        targets: list[tuple[str, str, str, dict[str, Any]]] = [
            ("health", "GET", "/health", {"auth": False}),
            ("reports_list", "GET", "/reports", {}),
        ]
        if report_id:
            targets += [
                ("report_risks", "GET", f"/reports/{report_id}/risks", {}),
                ("report_tone", "GET", f"/reports/{report_id}/tone", {}),
                ("report_metrics", "GET", f"/reports/{report_id}/metrics", {}),
                ("hybrid_search", "POST", "/search/hybrid",
                 {"json": {"query": "revenue growth and margin", "top_k": 5}}),
                ("vector_search", "POST", "/search/vector",
                 {"json": {"query": "free cash flow", "top_k": 5}}),
            ]
        if company_id:
            targets.append(("company_risk_summary", "GET", f"/companies/{company_id}/risk-summary", {}))

        table: dict[str, Any] = {}
        for key, method, path, kw in targets:
            samples = _bench(client, method, path, iterations, **kw)
            stats = latency_stats(samples)
            table[key] = stats
            ceiling = CEILINGS_MS.get(key)
            within = ceiling is None or stats["p95_ms"] <= ceiling
            suite.record(
                f"{key}",
                within,
                f"avg={stats['avg_ms']}ms median={stats['median_ms']}ms "
                f"p95={stats['p95_ms']}ms worst={stats['max_ms']}ms (n={stats['count']})"
                + ("" if within else f"  >ceiling {ceiling}ms"),
                warn=not within,
            )

        suite.measure("iterations", iterations)
        suite.measure("latency_ms", table)
    finally:
        if own:
            client.close()

    suite.print_summary()
    return suite


def main() -> int:
    iterations = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    suite = run(iterations=iterations)
    suite.save()
    return 0 if suite.ok else 1


if __name__ == "__main__":
    sys.exit(main())
