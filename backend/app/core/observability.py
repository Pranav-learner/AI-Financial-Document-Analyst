"""Prometheus observability module (Phase 11)."""

from __future__ import annotations

import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

# 1. Prometheus Metrics definition
HTTP_REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)

CACHE_OPERATIONS = Counter(
    "cache_operations_total",
    "Total cache operations (hits and misses)",
    ["cache_type", "status"],  # cache_type="redis", status="hit" / "miss" / "set"
)

GEMINI_TOKEN_USAGE = Counter(
    "gemini_token_usage_total",
    "Total Gemini API tokens consumed",
    ["model", "token_type"],  # token_type="input" / "output"
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP request metrics for Prometheus."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Avoid recording operational metrics endpoints (to reduce noise)
        path = request.url.path
        if path in ("/metrics", "/health", "/ready", "/status"):
            return await call_next(request)

        method = request.method
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status_code = str(response.status_code)
            
            HTTP_REQUEST_COUNT.labels(method=method, path=path, status_code=status_code).inc()
            HTTP_REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            
            return response
        except Exception:
            duration = time.time() - start_time
            HTTP_REQUEST_COUNT.labels(method=method, path=path, status_code="500").inc()
            HTTP_REQUEST_LATENCY.labels(method=method, path=path).observe(duration)
            raise


def metrics_endpoint() -> Response:
    """Exporter endpoint for Prometheus metrics format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
