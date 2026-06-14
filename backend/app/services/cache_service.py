"""Caching service backed by Redis (Phase 11)."""

from __future__ import annotations

import functools
import json
import hashlib
from typing import Any, Callable

from app.core.logging import get_logger
from app.core.redis import redis_client
from app.core.observability import CACHE_OPERATIONS

log = get_logger(__name__)


class CacheService:
    @staticmethod
    async def get(key: str) -> Any | None:
        """Retrieve and decode JSON from cache."""
        try:
            value = await redis_client.get(key)
            if value:
                CACHE_OPERATIONS.labels(cache_type="redis", status="hit").inc()
                return json.loads(value)
            CACHE_OPERATIONS.labels(cache_type="redis", status="miss").inc()
        except Exception as e:
            log.warning("cache.get_failed", key=key, error=str(e))
        return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 3600) -> bool:
        """Serialize and store JSON in cache with TTL."""
        try:
            serialized = json.dumps(value)
            await redis_client.set(key, serialized, ex=ttl)
            CACHE_OPERATIONS.labels(cache_type="redis", status="set").inc()
            return True
        except Exception as e:
            log.warning("cache.set_failed", key=key, error=str(e))
        return False

    @staticmethod
    async def delete(key: str) -> bool:
        """Delete a key from cache."""
        try:
            await redis_client.delete(key)
            return True
        except Exception as e:
            log.warning("cache.delete_failed", key=key, error=str(e))
        return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """Delete keys matching a scan pattern."""
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    await redis_client.delete(*keys)
                    count += len(keys)
                if cursor == 0:
                    break
            return count
        except Exception as e:
            log.warning("cache.delete_pattern_failed", pattern=pattern, error=str(e))
        return 0


def cache_endpoint(ttl: int = 3600, prefix: str = "endpoint") -> Callable:
    """Decorator to cache FastAPI endpoint responses.
    
    Generates a key based on route path, query params, and json body parameters.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # We exclude DB sessions or special dependencies from key generation
            key_parts = []
            for k, v in sorted(kwargs.items()):
                # Skip dependencies that cannot be serialized
                if k in ("db", "current_user", "service", "background_tasks"):
                    continue
                # For schemas/Pydantic objects, serialize them
                if hasattr(v, "model_dump"):
                    key_parts.append(f"{k}:{json.dumps(v.model_dump(mode='json'), sort_keys=True)}")
                else:
                    key_parts.append(f"{k}:{str(v)}")

            # Hash the key parts to avoid extremely long Redis keys
            hashed_params = hashlib.sha256(
                ":".join(key_parts).encode("utf-8")
            ).hexdigest()

            cache_key = f"cache:{prefix}:{func.__name__}:{hashed_params}"

            # Check cache
            cached_val = await CacheService.get(cache_key)
            if cached_val is not None:
                log.info("cache.hit", key=cache_key)
                return cached_val

            log.info("cache.miss", key=cache_key)
            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache (if it is a Pydantic model or dict)
            try:
                if hasattr(result, "model_dump"):
                    serialized_res = result.model_dump(mode='json')
                elif isinstance(result, list) and all(hasattr(item, "model_dump") for item in result):
                    serialized_res = [item.model_dump(mode='json') for item in result]
                else:
                    serialized_res = result

                await CacheService.set(cache_key, serialized_res, ttl=ttl)
            except Exception as e:
                log.warning("cache.decorator_set_failed", key=cache_key, error=str(e))

            return result

        return wrapper
    return decorator
