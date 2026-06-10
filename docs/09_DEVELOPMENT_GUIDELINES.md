# 09 — Development Guidelines

> **Audience:** All contributors
> **Scope:** Naming, branching, commits, testing, documentation, security baseline.

---

## Table of Contents

1. [Naming Conventions](#1-naming-conventions)
2. [Branch Strategy](#2-branch-strategy)
3. [Commit Conventions](#3-commit-conventions)
4. [Pull Requests & Review](#4-pull-requests--review)
5. [Testing Requirements](#5-testing-requirements)
6. [Documentation Requirements](#6-documentation-requirements)
7. [Security Baseline](#7-security-baseline)

---

## 1. Naming Conventions

**Python (backend)**
| Thing | Style | Example |
|---|---|---|
| Module / package | `snake_case` | `section_detector.py` |
| Function / variable | `snake_case` | `detect_sections()` |
| Class | `PascalCase` | `SectionDetector` |
| Constant | `UPPER_SNAKE` | `HEADING_MAX_LEN` |
| Pydantic schema | `PascalCase` + suffix | `SectionOut`, `ReportUploadResponse` |
| SQLAlchemy model | `PascalCase` singular | `ReportSection` (table `report_sections`) |

**Database** (see `02_DATABASE_DESIGN.md §3`): `snake_case`, plural tables, `*_id`
FKs; constraint/index names follow the `app/db/base.py` naming convention.

**TypeScript (frontend)**
| Thing | Style | Example |
|---|---|---|
| Component | `PascalCase` | `SectionMap.tsx` |
| Hook | `useX` camelCase | `useReportStatus.ts` |
| Variable / function | `camelCase` | `fetchSections()` |
| Type / interface | `PascalCase` | `SectionOut` |
| Constant | `UPPER_SNAKE` | `API_BASE_URL` |

**API routes** (see `04_API_DESIGN.md`): plural resources, lowercase paths,
versioned under `/api/v1`.

---

## 2. Branch Strategy

Trunk-based with short-lived feature branches.

- `main` — always green and deployable. Protected: PR + passing CI required.
- Feature branches off `main`, named by type + phase + short slug:

```
feat/phase1b-section-detection
fix/phase3-margin-rounding
docs/roadmap-update
chore/ci-pipeline
refactor/retrieval-context-assembler
```

Prefixes: `feat` · `fix` · `docs` · `chore` · `refactor` · `test` · `perf`.

- Keep branches small and scoped to a single phase deliverable.
- Rebase on `main` before opening a PR; squash-merge to keep history linear.
- No direct commits to `main`.

---

## 3. Commit Conventions

**Conventional Commits**: `type(scope): subject`

```
feat(sections): add rule-based section detector
fix(api): return 404 when section not found
docs(roadmap): append Phase 1B completion report
chore(deps): pin sqlalchemy to 2.0.x
test(sections): add 10-Q part-aware detection tests
refactor(ingestion): separate sync repo for the worker
```

Rules:
- Imperative, lowercase subject; no trailing period; ≤ 72 chars.
- `scope` = area (`api`, `ingestion`, `sections`, `agents`, `retrieval`, `db`, `frontend`, ...).
- Body explains *why* when not obvious; reference ADRs/issues.
- Breaking changes: `feat(api)!:` + `BREAKING CHANGE:` footer.

---

## 4. Pull Requests & Review

- PR description states: what, why, which phase, and how it was verified.
- Link the relevant doc/ADR; update docs **in the same PR** as the code.
- CI must pass: lint (ruff), format check (black), types (mypy), tests (pytest),
  frontend typecheck/build.
- At least one review approval; reviewer checks dependency rules
  (`07_REPOSITORY_STRUCTURE.md §6`) aren't violated.
- Squash-merge with a Conventional-Commit title.

---

## 5. Testing Requirements

Structure (`backend/tests/`):

| Suite | Marker | Scope | Needs services? |
|---|---|---|---|
| `unit/` | `@pytest.mark.unit` | pure logic, endpoints with deps mocked | No |
| `integration/` | `@pytest.mark.integration` | DB/Redis/Celery wiring, repositories, migrations | Yes |
| `evaluation/` | `@pytest.mark.evaluation` | retrieval recall, extraction accuracy vs gold sets | Yes (+ data) |

Requirements:
- New behavior ships with tests. Bug fixes ship with a regression test.
- Unit tests must not hit the network or a real DB.
- Test **failure cases**, not only success paths.
- `evaluation/` tests back the Metrics Dashboard targets and grow from Phase 2 onward.
- Run locally before pushing: `pytest -m unit` (fast) / `pytest` (full).
- Deterministic logic (growth/ratios in later phases; section detection now) gets
  explicit unit tests with known inputs.

Coverage: aim ≥ 80% on `services`, `repositories`, `ingestion`, `retrieval`, `agents` logic.

---

## 6. Documentation Requirements

- `docs/` is the **source of truth**; code conforms to it.
- **`06_IMPLEMENTATION_ROADMAP.md` is the single source of truth for implementation
  history.** Do **not** create per-phase implementation docs; append a phase
  completion report (and any new ADRs / lessons) inside `06` instead.
- Public functions/classes carry docstrings explaining *why*.
- New endpoints update `04_API_DESIGN.md` and ship accurate OpenAPI metadata.
- Diagrams use Mermaid and live in the relevant doc.

---

## 7. Security Baseline

> Auth is **scaffolded only** (`app/core/security.py`) and **implemented in Phase 11**.
> The plan is fixed now so dependents are stable.

**Authentication (planned, Phase 11)**
- OAuth2 password flow → short-lived **JWT access token** + **refresh token**.
- Passwords hashed with bcrypt (passlib). Tokens signed with `JWT_SECRET`/`HS256`.

**Authorization — RBAC**
- Roles: `viewer` (read), `analyst` (read + upload + generate), `admin` (manage).
- Role hierarchy in `security.py` (`ROLE_HIERARCHY`); endpoint guards via FastAPI
  dependencies (`require_role(...)`) added in Phase 11.
- Multi-tenant scoping: every query filtered by `org_id`.

**Secrets & data**
- Secrets only via env (`.env` local, secrets manager in prod); never in code or VCS.
- Raw documents served only via short-lived signed URLs (never inline).
- Logs are PII-aware: never log tokens, keys, or full document contents.
- All input validated by Pydantic at the API boundary; DB `CHECK` constraints are
  the last line of defense.

**Transport & CORS**
- HTTPS in staging/prod; CORS origins restricted via `CORS_ORIGINS`.
- Rate limiting + `Idempotency-Key` support added with the business endpoints.
