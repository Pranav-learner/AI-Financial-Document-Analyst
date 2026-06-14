"""§8 Retrieval Validation — baseline vs full pipeline.

Drives the platform's own retrieval evaluation harness (POST /evaluation/run)
for the vector baseline and the full RAG/hybrid pipeline, then reports the
ground-truth metrics (recall@k, MRR, nDCG, hit-rate) and the pipeline-stage
gains (query-rewriting / HyDE / reranking) the engine attributes to itself.

This validates the *wiring and metric surface* end-to-end against whatever
corpus is in the database. Absolute quality numbers depend on the corpus being
embedded with the same model as the query side; the deterministic demo seed
uses local hash embeddings, so on demo-only data recall is expected to be low —
the meaningful retrieval-quality numbers come from the controlled unit suite
(tests/unit/test_retrieval_metrics.py, test_rag.py).

    python -m validation.retrieval_eval
"""

from __future__ import annotations

import sys
from typing import Any

from validation._client import ValidationClient
from validation._results import Suite

METRIC_KEYS = ["mean_recall_at_k", "mean_precision_at_k", "mean_mrr", "hit_rate", "mean_ndcg"]
GAIN_KEYS = ["reranking_gain", "query_rewriting_gain", "hyde_gain"]


def _run_eval(client: ValidationClient, retrieval_type: str, top_k: int = 10) -> dict[str, Any] | None:
    resp = client.post("/evaluation/run", json={"retrieval_type": retrieval_type, "top_k": top_k})
    if resp.status != 200:
        return {"_error": f"HTTP {resp.status}: {resp.response.text[:160]}"}
    runs = resp.json().get("runs", [])
    return runs[0] if runs else None


def run(client: ValidationClient | None = None) -> Suite:
    suite = Suite("Retrieval Evaluation")
    own = client is None
    client = client or ValidationClient()
    try:
        client.ensure_auth()

        results: dict[str, Any] = {}
        for rtype in ("vector", "hybrid", "rag"):
            data = _run_eval(client, rtype)
            if data is None:
                suite.record(f"{rtype}: run", False, "no runs returned (empty corpus?)", warn=True)
                continue
            if "_error" in data:
                suite.record(f"{rtype}: run", False, data["_error"], warn=True)
                continue
            results[rtype] = data
            metrics = {k: data.get(k) for k in METRIC_KEYS}
            suite.record(
                f"{rtype}: pipeline executed & metrics returned",
                all(k in data for k in METRIC_KEYS),
                ", ".join(f"{k.replace('mean_', '')}={v}" for k, v in metrics.items()
                          if v is not None) or "no metrics",
            )
            suite.record(
                f"{rtype}: queries evaluated",
                (data.get("num_queries", 0) or 0) > 0,
                f"num_queries={data.get('num_queries')}, corpus_size={data.get('corpus_size')}, "
                f"latency={data.get('mean_latency_ms')}ms",
            )

        # Baseline vs full pipeline comparison.
        if "vector" in results and "hybrid" in results:
            base = results["vector"].get("mean_recall_at_k") or 0
            full = results["hybrid"].get("mean_recall_at_k") or 0
            suite.record(
                "hybrid recall ≥ vector baseline",
                full >= base,
                f"vector={base} hybrid={full}",
                warn=full < base,
            )

        # Pipeline-stage gains exposed by the RAG run.
        if "rag" in results:
            gains = {k: results["rag"].get(k) for k in GAIN_KEYS}
            suite.record(
                "RAG exposes stage-attribution gains",
                any(results["rag"].get(k) is not None for k in GAIN_KEYS),
                ", ".join(f"{k}={v}" for k, v in gains.items()),
            )

        suite.measure("runs", results)
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
