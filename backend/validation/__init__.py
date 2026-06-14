"""Phase 12 — Competition Readiness Validation Framework.

This package contains *validation* tooling only — it adds no product features.
Every module is evidence-gathering: it exercises the already-complete platform,
measures it, and reports pass/fail + numbers so claims can be proven rather
than assumed (Phase 12 core principle: "Everything must be proven").

Modules
-------
- ``_client``            shared authenticated HTTP client + timing helpers
- ``_results``           pass/fail aggregation + console/JSON rendering
- ``seed_demo``          deterministic, key-free demo dataset seeder (§3)
- ``smoke_test``         single-command smoke suite (§2)
- ``e2e_validation``     full document→answer pipeline integrity check (§1)
- ``performance_benchmark``  latency measurement: avg/median/p95/worst (§5)
- ``load_test``          lightweight concurrency probing (§6)
- ``agent_eval``         agent tool-selection / grounding evaluation (§7)
- ``retrieval_eval``     baseline-vs-full retrieval benchmark (§8)
- ``memo_eval``          memo grounding / completeness checks (§9)
- ``benchmark_eval``     ranking / score / tie / missing-data checks (§10)
- ``security_audit``     authn / RBAC / rate-limit / upload / secret checks (§11)
- ``deployment_audit``   static deployment-readiness audit (§13)
- ``run_all``            master orchestrator → writes reports/<name>.json

Run any module with ``python -m validation.<module>`` from the ``backend``
directory. ``python -m validation.run_all`` runs the full suite.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "12.0.0"
