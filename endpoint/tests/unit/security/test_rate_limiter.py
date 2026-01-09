"""Unit tests for rate limiter."""

import pytest
import time
import threading
from endpoint.security.rate_limiter import (
    InMemoryRateLimiter,
    RedisRateLimiter,
    get_rate_limiter,
)


class TestInMemoryRateLimiter:
    """Tests for InMemoryRateLimiter."""
    
    def test_allow_and_record_allows_first_request(self):
        """Test rate limiter allows first request."""
        limiter = InMemoryRateLimiter()
        
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.1",
            max_requests=10,
            window_seconds=60
        )
        
        assert allowed is True
        assert retry_after is None
    
    def test_allow_and_record_allows_within_limit(self):
        """Test rate limiter allows requests within limit."""
        limiter = InMemoryRateLimiter()
        
        # Make 5 requests (all should be allowed and recorded atomically)
        for _ in range(5):
            allowed, retry_after = limiter.allow_and_record(
                identifier="127.0.0.1",
                max_requests=10,
                window_seconds=60
            )
            assert allowed is True
            assert retry_after is None
    
    def test_allow_and_record_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit."""
        limiter = InMemoryRateLimiter()
        
        # Make max requests (all should be allowed)
        for _ in range(10):
            allowed, retry_after = limiter.allow_and_record(
                identifier="127.0.0.1",
                max_requests=10,
                window_seconds=60
            )
            assert allowed is True
        
        # 11th request should be blocked
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.1",
            max_requests=10,
            window_seconds=60
        )
        
        assert allowed is False
        assert retry_after is not None
        assert retry_after >= 0
    
    def test_allow_and_record_expires_old_requests(self):
        """Test rate limiter expires old requests outside window."""
        limiter = InMemoryRateLimiter()
        
        # Record requests
        for _ in range(10):
            limiter.allow_and_record("127.0.0.1", max_requests=10, window_seconds=1)
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again (old requests expired)
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.1",
            max_requests=10,
            window_seconds=1
        )
        
        assert allowed is True
        assert retry_after is None
    
    def test_allow_and_record_different_identifiers(self):
        """Test rate limiter tracks different identifiers separately."""
        limiter = InMemoryRateLimiter()
        
        # Fill limit for IP1
        for _ in range(10):
            limiter.allow_and_record("127.0.0.1", max_requests=10, window_seconds=60)
        
        # IP2 should still be allowed
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.2",
            max_requests=10,
            window_seconds=60
        )
        
        assert allowed is True
        assert retry_after is None
    
    def test_allow_and_record_atomic_behavior(self):
        """Test that allow_and_record is atomic (check + record in one call)."""
        limiter = InMemoryRateLimiter()
        
        # Make 1 request (should be allowed and recorded)
        allowed1, _ = limiter.allow_and_record("127.0.0.1", max_requests=1, window_seconds=60)
        assert allowed1 is True
        
        # Second request should be blocked (limit is 1)
        allowed2, retry_after = limiter.allow_and_record("127.0.0.1", max_requests=1, window_seconds=60)
        assert allowed2 is False
        assert retry_after is not None
    
    def test_clear_rate_limiter(self):
        """Test clearing rate limiter."""
        limiter = InMemoryRateLimiter()
        
        # Record requests
        for _ in range(10):
            limiter.allow_and_record("127.0.0.1", max_requests=10, window_seconds=60)
        
        # Clear
        limiter.clear()
        
        # Should be allowed again
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.1",
            max_requests=10,
            window_seconds=60
        )
        
        assert allowed is True
        assert retry_after is None
    
    def test_rate_limit_sliding_window(self):
        """Test rate limiter uses sliding window correctly."""
        limiter = InMemoryRateLimiter()
        
        # Make 5 requests with small delays
        for _ in range(5):
            allowed, _ = limiter.allow_and_record("127.0.0.1", max_requests=10, window_seconds=10)
            assert allowed is True
            time.sleep(0.1)
        
        # Should still be under limit
        allowed, _ = limiter.allow_and_record("127.0.0.1", max_requests=10, window_seconds=10)
        assert allowed is True
    
    def test_thread_safety(self):
        """Test rate limiter is thread-safe."""
        limiter = InMemoryRateLimiter()
        results = []
        
        def make_requests(identifier):
            for _ in range(5):
                allowed, _ = limiter.allow_and_record(identifier, max_requests=10, window_seconds=60)
                results.append(allowed)
        
        threads = []
        for i in range(3):
            t = threading.Thread(target=make_requests, args=(f"ip{i}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All should be True (each IP has its own limit)
        assert all(results)
    
    def test_atomic_three_calls_max_two(self):
        """Test: make 3 calls with max_requests=2, assert third is blocked (429 behavior)."""
        limiter = InMemoryRateLimiter()
        
        # First call: should be allowed
        allowed1, retry1 = limiter.allow_and_record("test-id", max_requests=2, window_seconds=60)
        assert allowed1 is True
        assert retry1 is None
        
        # Second call: should be allowed (at limit)
        allowed2, retry2 = limiter.allow_and_record("test-id", max_requests=2, window_seconds=60)
        assert allowed2 is True
        assert retry2 is None
        
        # Third call: should be blocked
        allowed3, retry3 = limiter.allow_and_record("test-id", max_requests=2, window_seconds=60)
        assert allowed3 is False
        assert retry3 is not None
        assert retry3 >= 0


class TestRedisRateLimiter:
    """Tests for RedisRateLimiter fallback behavior."""
    
    def test_redis_fallback_to_in_memory_on_error(self):
        """Test RedisRateLimiter falls back to in-memory on Redis errors."""
        # Create RedisRateLimiter with invalid URL (will fail to connect)
        limiter = RedisRateLimiter(redis_url="redis://invalid:6379")
        
        # Should fall back to in-memory
        assert not limiter.is_ready()
        
        # Should still work (using fallback)
        allowed, retry_after = limiter.allow_and_record(
            identifier="127.0.0.1",
            max_requests=2,
            window_seconds=60
        )
        assert allowed is True
        
        # Make second request
        allowed2, _ = limiter.allow_and_record("127.0.0.1", max_requests=2, window_seconds=60)
        assert allowed2 is True
        
        # Third should be blocked
        allowed3, retry3 = limiter.allow_and_record("127.0.0.1", max_requests=2, window_seconds=60)
        assert allowed3 is False
        assert retry3 is not None
    
    def test_redis_fallback_on_missing_package(self):
        """Test RedisRateLimiter handles missing redis package gracefully."""
        # This test verifies that if redis package is not installed,
        # the limiter still works via fallback
        limiter = RedisRateLimiter(redis_url="redis://localhost:6379")
        
        # Should fall back if redis not available
        # (We can't easily test missing package, but we can test invalid connection)
        if not limiter.is_ready():
            # Should work via fallback
            allowed, _ = limiter.allow_and_record("test", max_requests=1, window_seconds=60)
            assert allowed is True


class TestGetRateLimiter:
    """Tests for get_rate_limiter factory function."""
    
    def test_get_rate_limiter_returns_in_memory_by_default(self):
        """Test get_rate_limiter returns InMemoryRateLimiter when no Redis configured."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_get_rate_limiter_with_invalid_url_falls_back(self):
        """Test get_rate_limiter falls back to in-memory with invalid Redis URL."""
        limiter = get_rate_limiter(redis_url="redis://invalid-host:6379")
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_get_rate_limiter_with_none_url(self):
        """Test get_rate_limiter with explicit None URL."""
        limiter = get_rate_limiter(redis_url=None)
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_get_rate_limiter_uses_env_var_when_available(self, monkeypatch):
        """Test get_rate_limiter uses REDIS_URL env var when set."""
        import os
        # Set invalid Redis URL to test fallback behavior
        monkeypatch.setenv("REDIS_URL", "redis://invalid:6379")
        limiter = get_rate_limiter()
        # Should fall back to in-memory since connection will fail
        assert isinstance(limiter, InMemoryRateLimiter)
