"""Authenticated HTTP client for the Phase 12 validation suites.

Wraps ``httpx`` with: base-URL handling, register-or-login auth bootstrap,
bearer-token injection, and per-call wall-clock timing. Targets a *running*
backend (default ``http://localhost:8000``) so the suites validate the real,
deployed surface rather than an in-process test app.

Environment overrides:
  VALIDATION_BASE_URL   default http://localhost:8000
  VALIDATION_EMAIL      default validator@example.com
  VALIDATION_PASSWORD   default Phase12Valid!
  VALIDATION_ROLE       default ADMIN
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Timed:
    """An HTTP response paired with its measured latency in milliseconds."""

    response: httpx.Response
    ms: float

    @property
    def status(self) -> int:
        return self.response.status_code

    def json(self) -> Any:
        return self.response.json()


class ValidationClient:
    def __init__(
        self,
        base_url: str | None = None,
        prefix: str = "/api/v1",
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.environ.get("VALIDATION_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.prefix = prefix
        self.email = os.environ.get("VALIDATION_EMAIL", "validator@example.com")
        self.password = os.environ.get("VALIDATION_PASSWORD", "Phase12Valid!")
        self.role = os.environ.get("VALIDATION_ROLE", "ADMIN")
        self._client = httpx.Client(timeout=timeout)
        self._token: str | None = None

    # ---- url helpers -----------------------------------------------------
    def url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        if path.startswith("/api/"):
            return f"{self.base_url}{path}"
        return f"{self.base_url}{self.prefix}{path}"

    def _headers(self, auth: bool, extra: dict[str, str] | None = None) -> dict[str, str]:
        h: dict[str, str] = {}
        if auth and self._token:
            h["Authorization"] = f"Bearer {self._token}"
        if extra:
            h.update(extra)
        return h

    # ---- timed verbs -----------------------------------------------------
    def request(self, method: str, path: str, auth: bool = True, **kw: Any) -> Timed:
        headers = self._headers(auth, kw.pop("headers", None))
        t0 = time.perf_counter()
        resp = self._client.request(method, self.url(path), headers=headers, **kw)
        ms = (time.perf_counter() - t0) * 1000.0
        return Timed(resp, ms)

    def get(self, path: str, **kw: Any) -> Timed:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw: Any) -> Timed:
        return self.request("POST", path, **kw)

    # ---- auth bootstrap --------------------------------------------------
    def ensure_auth(self) -> str:
        """Register (idempotently) + login the validator user; cache the token."""
        if self._token:
            return self._token
        # Register — ignore 4xx (already exists / duplicate).
        try:
            self.post(
                "/auth/register",
                auth=False,
                json={"email": self.email, "password": self.password, "role": self.role},
            )
        except httpx.HTTPError:
            pass
        login = self.post(
            "/auth/login",
            auth=False,
            data={"username": self.email, "password": self.password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if login.status != 200:
            raise RuntimeError(
                f"Auth bootstrap failed: login HTTP {login.status} — {login.response.text[:200]}"
            )
        self._token = login.json()["access_token"]
        return self._token

    @property
    def token(self) -> str | None:
        return self._token

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ValidationClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
