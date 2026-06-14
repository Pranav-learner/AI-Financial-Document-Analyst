"""§6 Lightweight Load Testing — concurrency probing.

Fires concurrent requests at representative endpoints (queries, agent, memo,
benchmark surfaces) using a thread pool and reports throughput, success rate,
and latency under concurrency. Lightweight by design — it characterises
behaviour and surfaces bottlenecks / timeout risks; it does NOT attempt to
size capacity or redesign anything (Phase 12 constraint).

    python -m validation.load_test [concurrency] [total_requests]
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from validation._client import ValidationClient
from validation._results import Suite, latency_stats


def _hammer(make_call: Callable[[], tuple[int, float]], concurrency: int, total: int) -> dict[str, Any]:
    statuses: list[int] = []
    latencies: list[float] = []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(make_call) for _ in range(total)]
        for fut in as_completed(futures):
            try:
                status, ms = fut.result()
            except Exception:  # noqa: BLE001 - network/timeout counts as failure
                status, ms = 0, 0.0
            statuses.append(status)
            if status and status < 500:
                latencies.append(ms)
    wall = time.perf_counter() - start
    ok = sum(1 for s in statuses if 200 <= s < 400)
    # 429s are the per-user rate limiter doing its job under a burst — that is
    # protective behaviour, not a service failure. Real failures are 5xx / network.
    throttled = sum(1 for s in statuses if s == 429)
    real_fail = sum(1 for s in statuses if s == 0 or s >= 500)
    return {
        "total": total,
        "concurrency": concurrency,
        "succeeded": ok,
        "throttled_429": throttled,
        "failed": real_fail,
        "success_rate": round(ok / total, 3) if total else 0.0,
        "wall_s": round(wall, 3),
        "throughput_rps": round(total / wall, 1) if wall else 0.0,
        "latency": latency_stats(latencies),
        "status_breakdown": {str(s): statuses.count(s) for s in sorted(set(statuses))},
    }


def run(client: ValidationClient | None = None, concurrency: int = 10, total: int = 60) -> Suite:
    suite = Suite("Load Test")
    own = client is None
    client = client or ValidationClient()
    try:
        token = client.ensure_auth()
        base = client.base_url
        prefix = client.prefix
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Each scenario uses its own short-timeout httpx client per call to model
        # independent concurrent clients (the shared ValidationClient is not
        # thread-safe for our timing dataclass, so we issue raw httpx calls).
        import httpx

        def caller(method: str, path: str, **kw: Any) -> Callable[[], tuple[int, float]]:
            url = f"{base}{prefix}{path}"

            def _call() -> tuple[int, float]:
                with httpx.Client(timeout=30.0) as c:
                    t0 = time.perf_counter()
                    r = c.request(method, url, headers=auth_headers, **kw)
                    return r.status_code, (time.perf_counter() - t0) * 1000.0

            return _call

        scenarios: list[tuple[str, Callable[[], tuple[int, float]]]] = [
            ("concurrent reports list", caller("GET", "/reports")),
            ("concurrent hybrid queries",
             caller("POST", "/search/hybrid", json={"query": "operating margin trend", "top_k": 5})),
            ("concurrent vector queries",
             caller("POST", "/search/vector", json={"query": "liquidity risk", "top_k": 5})),
        ]

        results: dict[str, Any] = {}
        for name, call in scenarios:
            res = _hammer(call, concurrency, total)
            results[name] = res
            # Healthy = no real (5xx/network) failures. 429 throttling is acceptable
            # and is reported separately as a documented concurrency ceiling.
            healthy = res["failed"] == 0
            throttle_note = f", {res['throttled_429']} throttled(429)" if res["throttled_429"] else ""
            suite.record(
                name,
                healthy,
                f"{res['succeeded']}/{res['total']} 2xx @ c={concurrency}{throttle_note}, "
                f"{res['throughput_rps']} rps, p95={res['latency']['p95_ms']}ms, "
                f"worst={res['latency']['max_ms']}ms, 5xx/net-fail={res['failed']}",
                warn=not healthy,
            )
        any_throttle = any(r["throttled_429"] for r in results.values())
        suite.record(
            "rate limiter protects under burst (no 5xx)",
            all(r["failed"] == 0 for r in results.values()),
            "per-user 429 throttling observed — documented concurrency ceiling"
            if any_throttle else "no throttling at this level",
        )

        suite.measure("concurrency", concurrency)
        suite.measure("total_requests", total)
        suite.measure("scenarios", results)
    finally:
        if own:
            client.close()

    suite.print_summary()
    return suite


def main() -> int:
    concurrency = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    total = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    suite = run(concurrency=concurrency, total=total)
    suite.save()
    return 0 if suite.ok else 1


if __name__ == "__main__":
    sys.exit(main())
