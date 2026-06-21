import asyncio
import random
from typing import Callable, TypeVar
from app.core.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")

async def retry_gemini(func: Callable[[], T], max_retries: int = 12, base_delay: float = 3.0) -> T:
    """Execute a genai function in a separate thread and retry on 429 Resource Exhausted."""
    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(func)
        except Exception as exc:
            exc_str = str(exc)
            is_rate_limit = (
                "429" in exc_str
                or "resource_exhausted" in exc_str.lower()
                or "quota" in exc_str.lower()
            )
            if not is_rate_limit or attempt == max_retries - 1:
                raise exc
            
            delay = min(base_delay * (2 ** attempt), 30.0) + random.uniform(0.1, 1.0)
            log.warning(
                "gemini.rate_limit_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=f"{delay:.2f}s",
                error=exc_str
            )
            await asyncio.sleep(delay)
