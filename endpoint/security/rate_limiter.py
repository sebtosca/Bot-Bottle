"""
Rate limiting module for IP-based and user-based rate limiting.

Production: Redis backend (atomic via Lua)
Dev/Test: in-memory backend (deque-based)
"""

from __future__ import annotations

import os
import time
import uuid
import threading
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Optional, Tuple


class RateLimiter(ABC):
    @abstractmethod
    def allow_and_record(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """Atomically check + record. Returns (allowed, retry_after_seconds)."""
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Dev/test limiter. Not suitable for multi-instance production."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow_and_record(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            q = self._requests[identifier]

            # evict old timestamps (O(1) amortized)
            while q and q[0] <= window_start:
                q.popleft()

            if len(q) >= max_requests:
                oldest = q[0]
                retry_after = int((oldest + window_seconds) - now) + 1
                return False, max(0, retry_after)

            q.append(now)
            return True, None

    def clear(self) -> None:
        with self._lock:
            self._requests.clear()


# Atomic Redis sliding-window limiter (ZSET) in ONE call.
_REDIS_LUA = r"""
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

local window_start = now - window
redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

local count = redis.call("ZCARD", key)
if count >= limit then
  local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
  if oldest[2] then
    local retry = math.floor((tonumber(oldest[2]) + window) - now) + 1
    return {0, retry}
  end
  return {0, window}
end

redis.call("ZADD", key, now, member)
redis.call("EXPIRE", key, window + 60)
return {1, 0}
"""


class RedisRateLimiter(RateLimiter):
    """Production limiter. Correct under concurrency and multi-workers."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self._redis = None
        self._fallback = InMemoryRateLimiter()
        self._init_redis()

    def _init_redis(self) -> None:
        if not self.redis_url:
            return
        try:
            import redis  # type: ignore

            client = redis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            self._redis = client
        except Exception:
            self._redis = None

    def is_ready(self) -> bool:
        return self._redis is not None

    def allow_and_record(
        self, identifier: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        if not self._redis:
            return self._fallback.allow_and_record(identifier, max_requests, window_seconds)

        try:
            now = time.time()
            key = f"ratelimit:{identifier}"
            member = f"{now}:{uuid.uuid4().hex}"  # unique member avoids collisions

            allowed, retry = self._redis.eval(
                _REDIS_LUA, 1, key, now, window_seconds, max_requests, member
            )
            if int(allowed) == 1:
                return True, None
            return False, int(retry)
        except Exception:
            # explicit, predictable fallback
            return self._fallback.allow_and_record(identifier, max_requests, window_seconds)


def get_rate_limiter(redis_url: Optional[str] = None) -> RateLimiter:
    """Factory: Redis if configured and reachable, else in-memory."""
    url = redis_url or os.environ.get("REDIS_URL")
    if url:
        limiter = RedisRateLimiter(url)
        if limiter.is_ready():
            return limiter
    return InMemoryRateLimiter()
