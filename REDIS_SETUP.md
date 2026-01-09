# Redis Setup Guide

## Option 1: Using WSL2 (Recommended for Windows)

If you have WSL2 installed:

```bash
# In WSL2 terminal
sudo apt update
sudo apt install redis-server

# Start Redis
sudo service redis-server start

# Verify it's running
redis-cli ping
# Should return: PONG
```

Then set `REDIS_URL=redis://localhost:6379` in your `.env` file.

---

## Option 2: Using Docker (Easiest)

If you have Docker installed:

```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

This starts Redis on `localhost:6379`. Set `REDIS_URL=redis://localhost:6379` in your `.env` file.

To stop: `docker stop redis`
To start again: `docker start redis`

---

## Option 3: Using Memurai (Windows Native)

1. Download Memurai (Redis-compatible for Windows) from: https://www.memurai.com/get-memurai
2. Install it (it runs as a Windows service)
3. It will run on `localhost:6379` by default
4. Set `REDIS_URL=redis://localhost:6379` in your `.env` file

---

## Option 4: Using Redis for Windows (Unofficial)

1. Download from: https://github.com/tporadowski/redis/releases
2. Extract and run `redis-server.exe`
3. Set `REDIS_URL=redis://localhost:6379` in your `.env` file

---

## Python Package Installation

Install the `redis` Python package (optional - app works without it):

```bash
pip install redis
```

Or add to `requirements.txt`:
```
redis>=5.0.0
```

---

## Configuration

Add to your `.env` file:

```env
REDIS_URL=redis://localhost:6379
```

**Note:** The app will automatically fall back to in-memory rate limiting if:
- `REDIS_URL` is not set
- Redis is not reachable
- `redis` package is not installed

---

## Verify It's Working

1. Start your Flask app
2. Check the logs - if Redis is connected, you'll see no errors
3. Make rate-limited requests - they should work with Redis backend
4. You can also test with `redis-cli`:

```bash
redis-cli
> KEYS ratelimit:*
> GET ratelimit:127.0.0.1
```

---

## Quick Test Script

Create `test_redis.py`:

```python
import os
from endpoint.security.rate_limiter import get_rate_limiter

limiter = get_rate_limiter()
print(f"Using Redis: {limiter.is_ready() if hasattr(limiter, 'is_ready') else False}")
print(f"Limiter type: {type(limiter).__name__}")

# Test a request
allowed, retry = limiter.allow_and_record("test-ip", max_requests=10, window_seconds=60)
print(f"Allowed: {allowed}, Retry after: {retry}")
```

Run: `python test_redis.py`

Expected output if Redis is working:
```
Using Redis: True
Limiter type: RedisRateLimiter
Allowed: True, Retry after: None
```

Expected output if using fallback:
```
Using Redis: False
Limiter type: InMemoryRateLimiter
Allowed: True, Retry after: None
```
