"""Idempotency store interface and implementations.

Provides abstraction for checking and marking processed messages.
Supports Redis (production) and in-memory (dev/test) backends.
"""

from abc import ABC, abstractmethod
from typing import Optional
import time
import threading
from datetime import datetime, timedelta


class IdempotencyStore(ABC):
    """Abstract interface for idempotency storage."""
    
    @abstractmethod
    def is_duplicate(self, message_id: str) -> bool:
        """Check if a message ID has been seen before.
        
        Args:
            message_id: Unique message identifier.
        
        Returns:
            True if duplicate, False if new.
        """
        pass
    
    @abstractmethod
    def mark_processed(self, message_id: str, ttl_seconds: int = 86400) -> None:
        """Mark a message ID as processed.
        
        Args:
            message_id: Unique message identifier.
            ttl_seconds: Time-to-live in seconds (default: 24 hours).
        """
        pass


class InMemoryIdempotencyStore(IdempotencyStore):
    """In-memory idempotency store for development and testing.
    
    Uses a dict with expiration timestamps. Thread-safe.
    """
    
    def __init__(self):
        self._store: dict[str, float] = {}
        self._lock = threading.Lock()
    
    def is_duplicate(self, message_id: str) -> bool:
        """Check if message ID exists and hasn't expired."""
        with self._lock:
            if message_id not in self._store:
                return False
            
            # Check expiration
            expires_at = self._store[message_id]
            if time.time() > expires_at:
                # Expired, remove it
                del self._store[message_id]
                return False
            
            return True
    
    def mark_processed(self, message_id: str, ttl_seconds: int = 86400) -> None:
        """Mark message as processed with TTL."""
        with self._lock:
            expires_at = time.time() + ttl_seconds
            self._store[message_id] = expires_at
    
    def clear(self) -> None:
        """Clear all stored IDs (for testing)."""
        with self._lock:
            self._store.clear()


class RedisIdempotencyStore(IdempotencyStore):
    """Redis-based idempotency store for production.
    
    Requires redis package. Falls back to in-memory if Redis unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis store.
        
        Args:
            redis_url: Redis connection URL. If None, tries REDIS_URL env var.
        """
        self.redis_url = redis_url
        self._redis = None
        self._fallback = InMemoryIdempotencyStore()
        self._init_redis()
    
    def _init_redis(self) -> None:
        """Initialize Redis connection."""
        try:
            import redis
            import os
            
            url = self.redis_url or os.environ.get("REDIS_URL")
            if not url:
                return  # No Redis URL, use fallback
            
            self._redis = redis.from_url(url, decode_responses=True)
            # Test connection
            self._redis.ping()
        except ImportError:
            # redis package not installed
            pass
        except Exception:
            # Redis connection failed, use fallback
            self._redis = None
    
    def is_duplicate(self, message_id: str) -> bool:
        """Check if message ID exists in Redis."""
        if self._redis:
            try:
                exists = self._redis.exists(f"msg:{message_id}")
                return bool(exists)
            except Exception:
                # Redis error, fallback to in-memory
                return self._fallback.is_duplicate(message_id)
        else:
            return self._fallback.is_duplicate(message_id)
    
    def mark_processed(self, message_id: str, ttl_seconds: int = 86400) -> None:
        """Mark message as processed in Redis with TTL."""
        if self._redis:
            try:
                self._redis.setex(f"msg:{message_id}", ttl_seconds, "1")
            except Exception:
                # Redis error, fallback to in-memory
                self._fallback.mark_processed(message_id, ttl_seconds)
        else:
            self._fallback.mark_processed(message_id, ttl_seconds)


def get_idempotency_store(redis_url: Optional[str] = None) -> IdempotencyStore:
    """Factory function to get appropriate idempotency store.
    
    Args:
        redis_url: Optional Redis URL. If provided and valid, uses Redis.
                   Otherwise uses in-memory store.
    
    Returns:
        IdempotencyStore instance.
    """
    if redis_url:
        store = RedisIdempotencyStore(redis_url)
        if store._redis:
            return store
    
    # Try environment variable
    import os
    redis_url_env = os.environ.get("REDIS_URL")
    if redis_url_env:
        store = RedisIdempotencyStore(redis_url_env)
        if store._redis:
            return store
    
    # Fallback to in-memory
    return InMemoryIdempotencyStore()
