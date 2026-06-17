from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from typing import Any

_memory_cache: dict[str, tuple[Any, float | None]] = {}
_CACHE_TTL_SECONDS = int(os.getenv("MATHVERSE_CACHE_TTL_SECONDS", "86400"))
_REQUIRE_REDIS = os.getenv("MATHVERSE_CACHE_REQUIRE_REDIS", "").strip().lower() in {
    "1",
    "true",
    "yes",
}


def _resolve_cache_backend() -> str:
    configured_backend = os.getenv("MATHVERSE_CACHE_BACKEND", "").strip().lower()
    if configured_backend:
        return configured_backend
    if _REQUIRE_REDIS:
        return "redis"
    if os.getenv("REDIS_URL"):
        return "redis"
    return "memory"


_CACHE_BACKEND = _resolve_cache_backend()


@lru_cache(maxsize=1)
def _redis_client():
    if _CACHE_BACKEND == "memory":
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return client
    except Exception as error:
        if _REQUIRE_REDIS:
            raise RuntimeError(f"Redis cache is required but unavailable: {error}") from error
        print(f"Redis cache unavailable; using in-memory cache ({type(error).__name__}: {error})")
        return None


def _cache_key(key: object) -> str:
    return f"mathverse:cache:{str(key)}"


def _pack(value: Any) -> str:
    return json.dumps({"value": value}, ensure_ascii=False, default=str)


def _unpack(raw: str | None) -> Any:
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(payload, dict) and "value" in payload:
        return payload["value"]
    return payload


def get_cache(key):
    redis_client = _redis_client()
    if redis_client is not None:
        try:
            return _unpack(redis_client.get(_cache_key(key)))
        except Exception as error:
            if _REQUIRE_REDIS:
                raise RuntimeError(f"Redis cache read failed: {error}") from error

    item = _memory_cache.get(str(key))
    if item is None:
        return None
    value, expires_at = item
    if expires_at is not None and expires_at <= time.monotonic():
        _memory_cache.pop(str(key), None)
        return None
    return value


def set_cache(key, value, ttl_seconds: int | None = None):
    ttl = _CACHE_TTL_SECONDS if ttl_seconds is None else int(ttl_seconds)
    redis_client = _redis_client()
    if redis_client is not None:
        try:
            redis_client.set(_cache_key(key), _pack(value), ex=ttl if ttl > 0 else None)
            return
        except Exception as error:
            if _REQUIRE_REDIS:
                raise RuntimeError(f"Redis cache write failed: {error}") from error

    expires_at = time.monotonic() + ttl if ttl > 0 else None
    _memory_cache[str(key)] = (value, expires_at)
