"""Key store used for idempotency keys and customer-level recovery locks.

Redis is used when ``REVYN_REDIS_URL`` is configured; otherwise an in-process
backend with the same semantics keeps single-node deployments and tests working.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from app.core.clock import utcnow
from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class KeyStore(Protocol):
    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool: ...
    async def get(self, key: str) -> str | None: ...
    async def delete(self, key: str) -> None: ...
    async def close(self) -> None: ...


class MemoryKeyStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()

    def _purge(self, now: float) -> None:
        expired = [k for k, (_, exp) in self._data.items() if exp <= now]
        for key in expired:
            del self._data[key]

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        now = utcnow().timestamp()
        async with self._lock:
            self._purge(now)
            if key in self._data:
                return False
            self._data[key] = (value, now + ttl_seconds)
            return True

    async def get(self, key: str) -> str | None:
        now = utcnow().timestamp()
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at <= now:
                del self._data[key]
                return None
            return value

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._data.pop(key, None)

    async def close(self) -> None:
        self._data.clear()


class RedisKeyStore:
    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis

        self._redis = Redis.from_url(url, decode_responses=True)

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        return bool(await self._redis.set(key, value, nx=True, ex=ttl_seconds))

    async def get(self, key: str) -> str | None:
        return await self._redis.get(key)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.aclose()


_store: KeyStore | None = None


def get_keystore() -> KeyStore:
    global _store
    if _store is None:
        if settings.redis_url:
            try:
                _store = RedisKeyStore(settings.redis_url)
                log.info("keystore.redis", extra={"url": settings.redis_url})
            except Exception as exc:  # pragma: no cover - depends on local redis
                log.warning("keystore.redis_unavailable", extra={"error": str(exc)})
                _store = MemoryKeyStore()
        else:
            _store = MemoryKeyStore()
    return _store


async def close_keystore() -> None:
    global _store
    if _store is not None:
        await _store.close()
        _store = None
