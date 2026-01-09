#!/usr/bin/env python3
"""Quick script to test Redis connection for rate limiting."""

import os
from endpoint.security.rate_limiter import get_rate_limiter, RedisRateLimiter, InMemoryRateLimiter

def main():
    print("=" * 60)
    print("Redis Connection Test")
    print("=" * 60)
    
    # Check environment variable
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        print(f"✓ REDIS_URL found: {redis_url}")
    else:
        print("✗ REDIS_URL not set (will use in-memory fallback)")
    
    # Get limiter
    limiter = get_rate_limiter()
    limiter_type = type(limiter).__name__
    
    print(f"\nLimiter Type: {limiter_type}")
    
    # Check if Redis is actually connected
    if isinstance(limiter, RedisRateLimiter):
        is_ready = limiter.is_ready()
        if is_ready:
            print("✓ Redis is connected and ready")
        else:
            print("✗ Redis URL provided but connection failed (using in-memory fallback)")
    elif isinstance(limiter, InMemoryRateLimiter):
        print("ℹ Using in-memory rate limiter (Redis not configured or unavailable)")
    
    # Test a rate limit operation
    print("\n" + "-" * 60)
    print("Testing rate limit operation...")
    print("-" * 60)
    
    test_identifier = "test-ip-127.0.0.1"
    allowed, retry_after = limiter.allow_and_record(
        identifier=test_identifier,
        max_requests=10,
        window_seconds=60
    )
    
    print(f"✓ Request allowed: {allowed}")
    print(f"  Retry after: {retry_after}")
    
    # Make a few more requests to test
    print("\nMaking 5 test requests...")
    for i in range(5):
        allowed, retry = limiter.allow_and_record(test_identifier, max_requests=10, window_seconds=60)
        print(f"  Request {i+1}: allowed={allowed}, retry_after={retry}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
    
    if isinstance(limiter, InMemoryRateLimiter):
        print("\n💡 To use Redis:")
        print("   1. Install Redis (see REDIS_SETUP.md)")
        print("   2. Set REDIS_URL=redis://localhost:6379 in .env")
        print("   3. Install: pip install redis")

if __name__ == "__main__":
    main()
