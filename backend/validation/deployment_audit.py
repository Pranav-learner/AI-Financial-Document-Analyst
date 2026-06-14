"""§13 Deployment Readiness Audit — static checks (does NOT deploy).

Inspects the repository's deployment artifacts and produces a pass/fail
checklist: Docker, env templates, migrations, Celery, Redis, frontend build,
production config, and CI. All checks are filesystem/static — nothing is
deployed and no infrastructure is mutated (Phase 12 constraint).

    python -m validation.deployment_audit
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from validation._results import Suite

# backend/validation/ -> backend/ -> repo root
REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"


def _exists(suite: Suite, label: str, rel: str, warn: bool = False) -> Path | None:
    p = REPO / rel
    ok = p.exists()
    suite.record(label, ok, str(rel) if ok else f"missing: {rel}", warn=warn and not ok)
    return p if ok else None


def _contains(suite: Suite, label: str, rel: str, needle: str, warn: bool = False) -> None:
    p = REPO / rel
    if not p.exists():
        suite.record(label, False, f"missing file: {rel}", warn=warn)
        return
    text = p.read_text(errors="ignore")
    found = needle.lower() in text.lower() if not needle.startswith("re:") else bool(
        re.search(needle[3:], text, re.I)
    )
    suite.record(label, found, f"{'found' if found else 'not found'} in {rel}", warn=warn and not found)


def run() -> Suite:
    suite = Suite("Deployment Audit")

    # --- Docker -------------------------------------------------------------
    _exists(suite, "docker-compose (dev)", "docker-compose.yml")
    _exists(suite, "docker-compose (prod)", "docker-compose.prod.yml")
    _exists(suite, "backend Dockerfile", "backend/Dockerfile")
    _exists(suite, "backend Dockerfile.prod", "backend/Dockerfile.prod")
    _exists(suite, "frontend Dockerfile.prod", "frontend/Dockerfile.prod", warn=True)
    _contains(suite, "prod image runs as non-root", "backend/Dockerfile.prod", "appuser")
    _contains(suite, "prod image multi-worker uvicorn", "backend/Dockerfile.prod", "--workers")

    # --- Environment templates ---------------------------------------------
    _exists(suite, "env example (root)", ".env.example")
    _exists(suite, "env example (production)", ".env.production.example")
    for var in ("DATABASE_URL", "REDIS_URL", "GEMINI_API_KEY", "JWT_SECRET", "CELERY_BROKER_URL"):
        _contains(suite, f"prod env documents {var}", ".env.production.example", var)

    # --- Database migrations ------------------------------------------------
    _exists(suite, "alembic config", "backend/alembic.ini")
    versions = BACKEND / "migrations" / "versions"
    migrations = sorted(versions.glob("*.py")) if versions.exists() else []
    suite.record("alembic migrations present", len(migrations) >= 10, f"{len(migrations)} revisions")
    # The biggest deployment foot-gun for this stack: migrations are never auto-run.
    autorun = any(
        "alembic upgrade head" in (REPO / f).read_text(errors="ignore")
        for f in ("docker-compose.prod.yml", "backend/Dockerfile.prod")
        if (REPO / f).exists()
    )
    suite.record(
        "migrations auto-applied on deploy",
        autorun,
        "no `alembic upgrade head` in entrypoint/compose — must be run manually before first boot"
        if not autorun else "found in deploy config",
        warn=True,
    )

    # --- Celery / Redis -----------------------------------------------------
    _contains(suite, "celery worker service defined", "docker-compose.yml", "celery")
    _contains(suite, "redis service defined", "docker-compose.yml", "redis")
    _contains(suite, "prod redis password-protected", "docker-compose.prod.yml", "requirepass", warn=True)

    # --- Frontend build -----------------------------------------------------
    _contains(suite, "frontend build script", "frontend/package.json", "vite build")
    _exists(suite, "frontend build output committed", "frontend/dist/index.html", warn=True)
    _contains(suite, "frontend API base configurable", "frontend/src/services/api.ts", "VITE_API_BASE_URL")

    # --- Production config safety -------------------------------------------
    _contains(suite, "startup validates prod secrets", "backend/app/main.py", "verify_production_config")
    _contains(suite, "prod config rejects default JWT secret", "backend/app/main.py", "changeme")

    # --- CI -----------------------------------------------------------------
    ci = _exists(suite, "GitHub Actions CI", ".github/workflows/ci.yml")
    if ci:
        _contains(suite, "CI runs pytest", ".github/workflows/ci.yml", "pytest")
        _contains(suite, "CI runs ruff lint", ".github/workflows/ci.yml", "ruff")
        _contains(suite, "CI builds frontend", ".github/workflows/ci.yml", "build")
        _contains(suite, "CI runs frontend tests (vitest)", ".github/workflows/ci.yml",
                  "re:vitest|npm (run )?test", warn=True)

    # --- Deployment target manifests ---------------------------------------
    for label, rel in (
        ("render manifest", "infrastructure/deployment/render.yaml"),
        ("railway manifest", "infrastructure/deployment/railway.json"),
        ("vercel manifest", "infrastructure/deployment/vercel.json"),
    ):
        _exists(suite, label, rel, warn=True)

    suite.measure("migration_count", len(migrations))
    suite.print_summary()
    return suite


def main() -> int:
    suite = run()
    suite.save()
    return 0 if suite.ok else 1


if __name__ == "__main__":
    sys.exit(main())
