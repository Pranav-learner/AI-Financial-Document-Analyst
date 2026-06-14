"""Shared result aggregation + rendering for the Phase 12 validation suites.

Intentionally dependency-free (stdlib only) so every validation module can be
run in isolation without importing the FastAPI app.
"""

from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parent / "reports"

# ANSI colours — disabled automatically when stdout is not a TTY or NO_COLOR set.
_USE_COLOR = os.isatty(1) and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def green(t: str) -> str:
    return _c("32", t)


def red(t: str) -> str:
    return _c("31", t)


def yellow(t: str) -> str:
    return _c("33", t)


def bold(t: str) -> str:
    return _c("1", t)


@dataclass
class Check:
    """A single assertion with an outcome."""

    name: str
    passed: bool
    detail: str = ""
    # ``warn`` checks count as non-fatal: surfaced but do not fail the suite.
    warn: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def symbol(self) -> str:
        if self.warn and not self.passed:
            return yellow("WARN")
        return green("PASS") if self.passed else red("FAIL")


@dataclass
class Suite:
    """A named collection of checks plus free-form measurements."""

    name: str
    checks: list[Check] = field(default_factory=list)
    measurements: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)

    # ---- recording -------------------------------------------------------
    def record(
        self,
        name: str,
        passed: bool,
        detail: str = "",
        warn: bool = False,
        **data: Any,
    ) -> Check:
        chk = Check(name=name, passed=passed, detail=detail, warn=warn, data=data)
        self.checks.append(chk)
        line = f"  [{chk.symbol}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)
        return chk

    def measure(self, key: str, value: Any) -> None:
        self.measurements[key] = value

    # ---- summary ---------------------------------------------------------
    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if not c.passed and not c.warn)

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.warn)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "passed": self.passed,
            "failed": self.failed,
            "warned": self.warned,
            "duration_s": round(time.time() - self.started_at, 3),
            "measurements": self.measurements,
            "checks": [asdict(c) for c in self.checks],
        }

    def print_summary(self) -> None:
        status = green("OK") if self.ok else red("FAILED")
        print(
            bold(f"\n== {self.name}: {status} ")
            + f"({self.passed} passed, {self.failed} failed, {self.warned} warn)\n"
        )

    def save(self, filename: str | None = None) -> Path:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        fname = filename or f"{self.name.lower().replace(' ', '_')}.json"
        path = REPORTS_DIR / fname
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))
        return path


def latency_stats(samples_ms: list[float]) -> dict[str, float]:
    """avg / median / p95 / worst (and min) for a list of millisecond timings."""
    if not samples_ms:
        return {"count": 0, "avg_ms": 0.0, "median_ms": 0.0, "p95_ms": 0.0, "min_ms": 0.0, "max_ms": 0.0}
    ordered = sorted(samples_ms)
    p95_index = max(0, min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1)))))
    return {
        "count": len(samples_ms),
        "avg_ms": round(statistics.fmean(samples_ms), 1),
        "median_ms": round(statistics.median(samples_ms), 1),
        "p95_ms": round(ordered[p95_index], 1),
        "min_ms": round(ordered[0], 1),
        "max_ms": round(ordered[-1], 1),
    }
