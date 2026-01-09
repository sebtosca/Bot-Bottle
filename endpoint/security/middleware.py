"""Security middleware for Flask application.

Redis-ready rate limiting:
- Uses a single atomic call: limiter.allow_and_record(...)
- No separate check_rate_limit + record_request (avoids race conditions)
"""

import logging
from functools import wraps
from typing import Callable, Optional

from flask import Flask, request, jsonify, Response
from werkzeug.middleware.proxy_fix import ProxyFix

from .rate_limiter import RateLimiter, get_rate_limiter

logger = logging.getLogger(__name__)


def mask_identifier(identifier: str) -> str:
    """Mask identifier for logging (PII protection).
    
    Args:
        identifier: The identifier to mask (e.g., IP address, user ID)
        
    Returns:
        Masked identifier: first 4 chars + "****" if len > 5, else "****"
    """
    return (identifier[:4] + "****") if len(identifier) > 5 else "****"


def setup_security_headers(app: Flask) -> None:
    @app.after_request
    def add_security_headers(resp: Response) -> Response:
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' https://*.whatsapp.net https://*.facebook.com data:; "
            "media-src 'self' https://*.whatsapp.net https://*.facebook.com; "
            "script-src 'none'; style-src 'none'; object-src 'none'; "
            "base-uri 'self'; form-action 'self';",
        )

        # Add HSTS only when request is actually HTTPS (after ProxyFix)
        # #region agent log
        import json
        import time
        try:
            wsgi_scheme = request.environ.get('wsgi.url_scheme', 'NOT_SET') if hasattr(request, 'environ') else 'NO_ENVIRON'
            is_secure_val = request.is_secure if hasattr(request, 'is_secure') else 'NO_IS_SECURE'
            url_scheme = getattr(request, 'scheme', 'NO_SCHEME')
            url_val = str(request.url) if hasattr(request, 'url') else 'NO_URL'
            with open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"middleware.py:49","message":"HSTS check","data":{"is_secure":is_secure_val,"wsgi_url_scheme":wsgi_scheme,"request_scheme":url_scheme,"request_url":url_val[:100],"has_environ":hasattr(request,'environ'),"environ_keys":list(request.environ.keys())[:15] if hasattr(request,'environ') else []},"timestamp":time.time()*1000}) + '\n')
        except Exception as e:
            try:
                with open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"middleware.py:49","message":"HSTS check error","data":{"error":str(e)},"timestamp":time.time()*1000}) + '\n')
            except: pass
        # #endregion
        if request.is_secure:
            # #region agent log
            try:
                with open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"middleware.py:66","message":"HSTS header added","data":{},"timestamp":time.time()*1000}) + '\n')
            except: pass
            # #endregion
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        else:
            # #region agent log
            try:
                with open(r'c:\Users\SebastienToscano\BotBottle\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"middleware.py:75","message":"HSTS NOT added - is_secure is False","data":{"is_secure":False},"timestamp":time.time()*1000}) + '\n')
            except: pass
            # #endregion

        return resp


def setup_proxy_fix(app: Flask, *, x_for: int = 1, x_proto: int = 1) -> None:
    """Enable only if you're behind a trusted proxy/load balancer."""
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=x_for, x_proto=x_proto)


def get_client_ip(req) -> str:
    """After ProxyFix, remote_addr reflects the real client IP."""
    return getattr(req, "remote_addr", None) or "unknown"


def rate_limit(
    *,
    max_requests: int = 100,
    window_seconds: int = 60,
    identifier_func: Optional[Callable] = None,
    rate_limiter: Optional[RateLimiter] = None,
):
    """
    Redis-safe rate limiting decorator.

    IMPORTANT:
    - Requires RateLimiter to implement allow_and_record(identifier, max_requests, window_seconds)
    - This must be a single atomic operation in Redis (Lua) to be correct under concurrency.
    """
    limiter = rate_limiter or get_rate_limiter()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            identifier = identifier_func(request) if identifier_func else get_client_ip(request)

            # ✅ Atomic: check + record in one call (Redis Lua), prevents races
            allowed, retry_after = limiter.allow_and_record(
                identifier=identifier,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )

            if not allowed:
                masked = mask_identifier(identifier)
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "identifier": masked,
                        "endpoint": request.endpoint,
                        "retry_after": retry_after,
                    },
                )
                ra = int(retry_after or window_seconds)
                resp = jsonify(
                    error="rate_limited",
                    retry_after=ra,
                    message=f"Too many requests. Try again in {ra}s.",
                )
                resp.status_code = 429
                resp.headers["Retry-After"] = str(ra)
                return resp

            return func(*args, **kwargs)

        return wrapper

    return decorator
