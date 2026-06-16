"""Secure headers middleware (Phase 11)."""

from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to inject security headers on every response (OWASP compliance)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Content Security Policy (restrict all origins, frames, object embed tags)
        # Relax for documentation paths to allow Swagger/ReDoc assets from CDN
        path = request.url.path
        if path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "frame-ancestors 'none'; object-src 'none';"
            )
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; object-src 'none';"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Control referrer information leak
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Enable XSS filtering in legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Strict Transport Security (HSTS) - only applied on HTTPS/production
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response
