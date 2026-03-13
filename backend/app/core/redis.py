"""
Redis client singleton and caching decorator for PRITHVINET.

Provides:
  - Async Redis connection pool (singleton)
  - @cached(ttl_seconds=N) decorator for endpoint-level caching
  - Graceful fallback: if Redis is down, endpoints still work (just uncached)

Usage:
    from app.core.redis import cached, get_redis, close_redis

    @router.get("/heavy-query")
    @cached(ttl_seconds=60)
    async def heavy_query(city: str = "Raipur"):
        ...
"""

from __future__ import annotations

import functools
import hashlib
import json
from datetime import datetime
from typing import Optional

from loguru import logger
from redis.asyncio import Redis

from app.core.config import settings

# ── Singleton connection ──────────────────────────────────────────────

_redis: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get or create the async Redis connection."""
    global _redis
    if _redis is None:
        _redis = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Verify connection
        try:
            await _redis.ping()
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.warning(f"Redis connection failed (caching disabled): {e}")
            # Keep the client — it will retry on next operation
    return _redis


async def close_redis():
    """Cleanly close the Redis connection."""
    global _redis
    if _redis:
        try:
            await _redis.close()
        except Exception:
            pass
        _redis = None
        logger.info("Redis connection closed")


async def health_check() -> bool:
    """Check if Redis is reachable."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False


async def get_cache_stats() -> dict:
    """Get basic cache statistics."""
    try:
        r = await get_redis()
        info = await r.info("stats")
        keyspace = await r.dbsize()
        return {
            "connected": True,
            "total_keys": keyspace,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate_pct": round(
                100
                * info.get("keyspace_hits", 0)
                / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
                1,
            ),
        }
    except Exception:
        return {
            "connected": False,
            "total_keys": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate_pct": 0,
        }


# ── JSON serializer that handles datetimes ────────────────────────────


def _json_default(obj):
    """Handle datetime and other non-serializable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "__float__"):
        return float(obj)
    if hasattr(obj, "__int__"):
        return int(obj)
    return str(obj)


# ── @cached decorator ─────────────────────────────────────────────────


def cached(ttl_seconds: int = 60, prefix: str = ""):
    """
    Decorator that caches the JSON response of an async FastAPI endpoint.

    - Cache key is built from function name + all positional/keyword args
    - TTL is per-endpoint (e.g., 60s for summaries, 600s for forecasts)
    - On Redis failure, silently falls through to the real function
    - Works with both GET and POST endpoints

    Args:
        ttl_seconds: Time-to-live for the cached response
        prefix: Optional prefix for cache key namespace
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build a unique cache key from function module + name + args
            key_parts = f"{prefix or func.__module__}.{func.__name__}"

            # Include all arguments in the cache key
            if args:
                key_parts += f":{args}"
            if kwargs:
                # Sort kwargs for deterministic key generation
                sorted_kw = sorted(
                    (k, v)
                    for k, v in kwargs.items()
                    if v is not None  # Skip None params — they're defaults
                )
                if sorted_kw:
                    key_parts += f":{sorted_kw}"

            cache_key = (
                f"prithvinet:{hashlib.sha256(key_parts.encode()).hexdigest()[:32]}"
            )

            # Try reading from cache
            try:
                r = await get_redis()
                hit = await r.get(cache_key)
                if hit is not None:
                    logger.debug(
                        f"Cache HIT: {func.__name__} (key={cache_key[:20]}...)"
                    )
                    return json.loads(hit)
            except Exception as e:
                logger.debug(f"Cache read failed for {func.__name__}: {e}")

            # Cache miss — execute the real function
            result = await func(*args, **kwargs)

            # Write result to cache (fire-and-forget, don't block response)
            try:
                r = await get_redis()
                serialized = json.dumps(result, default=_json_default)
                await r.setex(cache_key, ttl_seconds, serialized)
                logger.debug(f"Cache SET: {func.__name__} (ttl={ttl_seconds}s)")
            except Exception as e:
                logger.debug(f"Cache write failed for {func.__name__}: {e}")

            return result

        return wrapper

    return decorator
