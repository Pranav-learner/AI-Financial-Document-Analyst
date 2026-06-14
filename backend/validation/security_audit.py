"""§11 Security Validation — runtime checks against a live backend.

Verifies the Phase 11 hardening actually holds at the HTTP edge:
  - Authentication: protected routes reject anonymous + malformed tokens.
  - RBAC: a VIEWER cannot perform an ANALYST-only write.
  - Rate limiting: rapid login attempts eventually return HTTP 429.
  - Upload validation: non-PDF / wrong content-type uploads are rejected.
  - Secret handling: error bodies and /status do not leak secrets.
  - Security headers: OWASP headers present on responses.

    python -m validation.security_audit

Note: the rate-limit check intentionally trips the login limiter for this
client's IP for ~60s; run it last in a shared-client sequence.
"""

from __future__ import annotations

import io
import sys
import uuid

import httpx

from validation._client import ValidationClient
from validation._results import Suite

# Headers we expect the SecurityHeadersMiddleware to inject (OWASP baseline).
EXPECTED_HEADERS = [
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
]


def run(client: ValidationClient | None = None) -> Suite:
    suite = Suite("Security Audit")
    own = client is None
    client = client or ValidationClient()
    try:
        client.ensure_auth()

        # 1. Authentication ------------------------------------------------
        anon = client.get("/reports", auth=False)
        suite.record("authn: anonymous → 401", anon.status == 401, f"HTTP {anon.status}")

        bad = client.get("/reports", headers={"Authorization": "Bearer not-a-real-token"})
        suite.record("authn: malformed token → 401", bad.status == 401, f"HTTP {bad.status}")

        # 2. RBAC: a VIEWER may not run an ANALYST-only action -------------
        viewer_email = f"viewer-{uuid.uuid4().hex[:8]}@example.com"
        client.post("/auth/register", auth=False,
                    json={"email": viewer_email, "password": "ViewerPass123!", "role": "VIEWER"})
        login = client.post("/auth/login", auth=False,
                            data={"username": viewer_email, "password": "ViewerPass123!"},
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
        if login.status == 200:
            vtoken = login.json()["access_token"]
            vh = {"Authorization": f"Bearer {vtoken}"}
            # /evaluation/run requires ANALYST.
            forbidden = client.post("/evaluation/run", json={"retrieval_type": "vector"}, headers=vh)
            suite.record("rbac: viewer blocked from analyst action (403)",
                         forbidden.status == 403, f"HTTP {forbidden.status}")
            # VIEWER may still read.
            allowed = client.get("/reports", headers=vh)
            suite.record("rbac: viewer allowed to read (200)", allowed.status == 200,
                         f"HTTP {allowed.status}")
        else:
            suite.record("rbac: viewer login", False, f"HTTP {login.status}", warn=True)

        # 3. Upload validation: wrong content reaches 4xx ------------------
        token = client.token
        files = {"file": ("evil.exe", io.BytesIO(b"MZ not a pdf"), "application/octet-stream")}
        data = {"report_type": "10-K", "year": "2024"}
        up = httpx.post(
            client.url("/reports/upload"),
            headers={"Authorization": f"Bearer {token}"},
            files=files, data=data, timeout=30.0,
        )
        suite.record("upload validation: non-PDF rejected (4xx)",
                     400 <= up.status_code < 500, f"HTTP {up.status_code}")

        # 4. Security headers ---------------------------------------------
        h = client.get("/health", auth=False)
        present = {k.lower() for k in h.response.headers.keys()}
        for header in EXPECTED_HEADERS:
            suite.record(f"header: {header}", header in present,
                         h.response.headers.get(header, "missing"))

        # 5. Secret leakage: error body / status must not echo secrets -----
        st = client.get("/status", auth=False)
        body = (st.response.text if st.status != 404 else "") + bad.response.text
        leaked = any(s in body.lower() for s in ("jwt_secret", "password_hash", "gemini_api_key", "changeme"))
        suite.record("secret handling: no secrets in responses", not leaked,
                     "scanned /status + auth error bodies")

        # 6. Rate limiting (runs last — trips login limiter for this IP) ---
        statuses = []
        for _ in range(8):
            r = client.post("/auth/login", auth=False,
                            data={"username": f"rl-{uuid.uuid4().hex[:6]}@example.com", "password": "x"},
                            headers={"Content-Type": "application/x-www-form-urlencoded"})
            statuses.append(r.status)
        tripped = 429 in statuses
        suite.record("rate limiting: login limiter trips (429)", tripped,
                     f"statuses={statuses}")

        suite.measure("login_status_sequence", statuses)
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
