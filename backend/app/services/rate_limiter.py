"""Redis-backed rate limiting service (Phase 11)."""

from __future__ import annotations

import time
from fastapi import Request, HTTPException, status

from app.core.logging import get_logger
from app.core.redis import redis_client

log = get_logger(__name__)


class RateLimiter:
    @staticmethod
    async def is_rate_limited(
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Check if request count exceeds the limit within window_seconds using a sliding window log."""
        try:
            now = time.time()
            clear_before = now - window_seconds

            # Pipeline to execute sliding window commands atomically
            pipe = redis_client.pipeline()
            # Remove timestamps older than the window
            pipe.zremrangebyscore(key, 0, clear_before)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Count total requests in window
            pipe.zcard(key)
            # Set key expiry to match the window
            pipe.expire(key, window_seconds)

            # Execute pipeline
            _, _, count, _ = await pipe.execute()

            if count > limit:
                log.warning("rate_limiter.limit_exceeded", key=key, count=count, limit=limit)
                return True
            return False
        except Exception as e:
            log.warning("rate_limiter.error", key=key, error=str(e))
            # Fail-open under redis failures to prevent API outages
            return False


class RateLimitCheck:
    """FastAPI Dependency for rate limiting."""

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        scope: str = "user",  # "user", "endpoint", or "global"
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        endpoint_name = request.scope.get("endpoint").__name__ if request.scope.get("endpoint") else "generic"
        
        if self.scope == "user":
            # Extract user identifier (from state, token, or IP address as fallback)
            user_id = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = str(request.state.user.id)
            else:
                # Fallback to authorization token subject or IP
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        from app.core.security import decode_token
                        token = auth_header.split(" ")[1]
                        payload = decode_token(token)
                        user_id = payload.get("sub")
                    except Exception:
                        pass
            
            identifier = user_id or request.client.host if request.client else "unknown"
            key = f"rate_limit:user:{identifier}:{endpoint_name}"
        elif self.scope == "endpoint":
            key = f"rate_limit:endpoint:{endpoint_name}"
        else:
            key = "rate_limit:global"

        limited = await RateLimiter.is_rate_limited(
            key=key,
            limit=self.limit,
            window_seconds=self.window_seconds,
        )

        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
