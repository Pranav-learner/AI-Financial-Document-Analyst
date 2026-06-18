"""Redis async client setup (Phase 11)."""

from __future__ import annotations

import ssl
import redis.asyncio as aioredis

from app.core.config import settings

# Initialize global Redis client with decoding enabled
redis_kwargs = {
    "encoding": "utf-8",
    "decode_responses": True,
}
if settings.redis_url.startswith("rediss://"):
    redis_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE

redis_client: aioredis.Redis = aioredis.from_url(
    settings.redis_url,
    **redis_kwargs
)


async def get_redis() -> aioredis.Redis:
    """Dependency provider for Redis client."""
    return redis_client
