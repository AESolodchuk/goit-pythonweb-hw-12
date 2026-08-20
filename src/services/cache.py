"""Redis-backed cache helpers for authenticated users."""

import json
from typing import Any

from redis.asyncio import Redis

from src.conf.config import settings


def get_redis() -> Redis:
    """Create a Redis client using the configured connection URL."""
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_cached(key: str) -> dict[str, Any] | None:
    """Return a cached JSON object, or ``None`` when Redis is unavailable."""
    client = get_redis()
    try:
        value = await client.get(key)
        return json.loads(value) if value else None
    except Exception:
        return None
    finally:
        await client.aclose()


async def set_cached(key: str, value: dict[str, Any], expire: int) -> None:
    """Store a JSON object with a bounded lifetime."""
    client = get_redis()
    try:
        await client.set(key, json.dumps(value), ex=expire)
    except Exception:
        pass
    finally:
        await client.aclose()


async def delete_cached(key: str) -> None:
    """Remove one cache entry."""
    client = get_redis()
    try:
        await client.delete(key)
    except Exception:
        pass
    finally:
        await client.aclose()
