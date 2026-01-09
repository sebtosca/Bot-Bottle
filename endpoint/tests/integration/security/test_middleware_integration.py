"""Integration tests for security middleware."""

import pytest
from unittest.mock import patch
from flask import Flask, request, Response
from endpoint.security.middleware import (
    setup_security_headers,
    setup_proxy_fix,
    rate_limit,
    get_client_ip,
)
from endpoint.security.rate_limiter import InMemoryRateLimiter


class TestSecurityHeaders:
    """Integration tests for security headers."""
    
    def test_security_headers_added(self, app, client):
        """Test security headers are added to responses."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test')
        
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'
        assert 'Content-Security-Policy' in response.headers
    
    def test_csp_header_content(self, app, client):
        """Test Content-Security-Policy header has correct content."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test')
        csp = response.headers.get('Content-Security-Policy')
        
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "img-src 'self' https://*.whatsapp.net https://*.facebook.com data:" in csp
        assert "script-src 'none'" in csp
    
    def test_hsts_header_not_added_on_http(self, app, client):
        """Test HSTS header is not added on HTTP requests."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test')
        
        # HSTS should not be present on HTTP
        assert 'Strict-Transport-Security' not in response.headers
    
    def test_hsts_header_added_on_https(self, app):
        """Test HSTS header added on HTTPS requests."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Use url_scheme parameter to simulate HTTPS request
        response = client.get('/test', url_scheme='https')
        assert 'Strict-Transport-Security' in response.headers
        hsts = response.headers.get('Strict-Transport-Security')
        assert 'max-age=31536000' in hsts
        assert 'includeSubDomains' in hsts
    
    def test_security_headers_on_all_endpoints(self, app, client):
        """Test security headers are added to all endpoints."""
        setup_security_headers(app)
        
        @app.route('/endpoint1')
        def endpoint1():
            return {"status": "ok"}
        
        @app.route('/endpoint2')
        def endpoint2():
            return {"data": "test"}
        
        @app.route('/error')
        def error():
            return {"error": "not found"}, 404
        
        for path in ['/endpoint1', '/endpoint2', '/error']:
            response = client.get(path)
            assert response.headers.get('X-Content-Type-Options') == 'nosniff'
            assert response.headers.get('X-Frame-Options') == 'DENY'
    
    def test_security_headers_preserve_existing(self, app, client):
        """Test security headers don't override existing headers."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            resp = Response('{"status": "ok"}', mimetype='application/json')
            resp.headers['X-Frame-Options'] = 'SAMEORIGIN'
            return resp
        
        response = client.get('/test')
        
        # Should preserve existing header
        assert response.headers.get('X-Frame-Options') == 'SAMEORIGIN'


class TestRateLimitIntegration:
    """Integration tests for rate limiting."""
    
    def test_rate_limit_allows_within_limit(self, app, rate_limiter):
        """Test rate limit allows requests within limit."""
        @app.route('/test')
        @rate_limit(max_requests=10, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Make 5 requests
        for _ in range(5):
            response = client.get('/test')
            assert response.status_code == 200
    
    def test_rate_limit_blocks_over_limit(self, app, rate_limiter):
        """Test rate limit blocks requests over limit."""
        @app.route('/test')
        @rate_limit(max_requests=3, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Make 3 requests (at limit)
        for _ in range(3):
            response = client.get('/test')
            assert response.status_code == 200
        
        # 4th request should be blocked
        response = client.get('/test')
        assert response.status_code == 429
        data = response.get_json()
        assert data["error"] == "rate_limited"
        assert "retry_after" in data
        assert "Retry-After" in response.headers
    
    def test_rate_limit_per_ip(self, app, rate_limiter):
        """Test rate limit is per IP address."""
        @app.route('/test')
        @rate_limit(max_requests=2, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # IP1 makes 2 requests (at limit)
        for _ in range(2):
            response = client.get('/test', environ_base={'REMOTE_ADDR': '127.0.0.1'})
            assert response.status_code == 200
        
        # IP2 should still be allowed (different IP)
        response = client.get('/test', environ_base={'REMOTE_ADDR': '127.0.0.2'})
        assert response.status_code == 200
    
    def test_rate_limit_with_custom_identifier(self, app, rate_limiter):
        """Test rate limit with custom identifier function."""
        def custom_identifier(req):
            return f"user-{req.headers.get('X-User-ID', 'anonymous')}"
        
        @app.route('/test')
        @rate_limit(
            max_requests=2,
            window_seconds=60,
            identifier_func=custom_identifier,
            rate_limiter=rate_limiter
        )
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # User 1 makes 2 requests (at limit)
        for _ in range(2):
            response = client.get('/test', headers={'X-User-ID': 'user1'})
            assert response.status_code == 200
        
        # User 1's 3rd request should be blocked
        response = client.get('/test', headers={'X-User-ID': 'user1'})
        assert response.status_code == 429
        
        # User 2 should still be allowed
        response = client.get('/test', headers={'X-User-ID': 'user2'})
        assert response.status_code == 200
    
    def test_rate_limit_response_format(self, app, rate_limiter):
        """Test rate limit response has correct format."""
        @app.route('/test')
        @rate_limit(max_requests=1, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # First request
        client.get('/test')
        
        # Second request (blocked)
        response = client.get('/test')
        
        assert response.status_code == 429
        data = response.get_json()
        assert data["error"] == "rate_limited"
        assert "retry_after" in data
        assert isinstance(data["retry_after"], int)
        assert data["retry_after"] >= 0
        assert "message" in data
        assert "Too many requests" in data["message"]
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"].isdigit()
    
    def test_rate_limit_window_expiration(self, app, rate_limiter):
        """Test rate limit resets after window expires."""
        import time
        
        @app.route('/test')
        @rate_limit(max_requests=2, window_seconds=1, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Make 2 requests (at limit)
        for _ in range(2):
            response = client.get('/test')
            assert response.status_code == 200
        
        # 3rd request should be blocked
        response = client.get('/test')
        assert response.status_code == 429
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        response = client.get('/test')
        assert response.status_code == 200
    
    def test_rate_limit_atomic_behavior(self, app, rate_limiter):
        """Test rate limit atomic behavior: 3 calls with max_requests=2, third is blocked."""
        @app.route('/test')
        @rate_limit(max_requests=2, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # First request: should be allowed
        response1 = client.get('/test')
        assert response1.status_code == 200
        
        # Second request: should be allowed (at limit)
        response2 = client.get('/test')
        assert response2.status_code == 200
        
        # Third request: should be blocked (over limit)
        response3 = client.get('/test')
        assert response3.status_code == 429
        data = response3.get_json()
        assert data["error"] == "rate_limited"
        assert "retry_after" in data
        assert isinstance(data["retry_after"], int)
        assert data["retry_after"] >= 0


class TestProxyFix:
    """Integration tests for ProxyFix setup."""
    
    def test_proxy_fix_applied(self, app):
        """Test ProxyFix is applied to application."""
        original_wsgi_app = app.wsgi_app
        
        setup_proxy_fix(app, x_for=1, x_proto=1)
        
        # WSGI app should be wrapped
        assert app.wsgi_app != original_wsgi_app
    
    def test_proxy_fix_with_custom_params(self, app):
        """Test ProxyFix with custom parameters."""
        setup_proxy_fix(app, x_for=2, x_proto=2)
        
        # Should not raise
        assert app.wsgi_app is not None


class TestGetClientIP:
    """Integration tests for get_client_ip function."""
    
    def test_get_client_ip_from_remote_addr(self, app):
        """Test getting IP from remote_addr (after ProxyFix)."""
        from flask import request
        with app.test_request_context('/test', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            ip = get_client_ip(request)
            assert ip == '192.168.1.1'
    
    def test_get_client_ip_fallback_to_unknown(self, app):
        """Test getting IP falls back to unknown when remote_addr is None."""
        from flask import request
        with app.test_request_context('/test', environ_base={'REMOTE_ADDR': None}):
            ip = get_client_ip(request)
            assert ip == "unknown"
    
    def test_get_client_ip_fallback_when_missing(self, app):
        """Test getting IP falls back when remote_addr is missing."""
        from flask import request
        with app.test_request_context('/test'):
            # Remove REMOTE_ADDR if it exists
            if hasattr(request, 'environ'):
                request.environ.pop('REMOTE_ADDR', None)
            ip = get_client_ip(request)
            assert ip == "unknown"
    
    def test_get_client_ip_with_different_ips(self, app):
        """Test get_client_ip returns correct IP for different requests."""
        from flask import request
        
        test_cases = [
            ('192.168.1.1', '192.168.1.1'),
            ('10.0.0.1', '10.0.0.1'),
            ('::1', '::1'),
        ]
        
        for remote_addr, expected in test_cases:
            with app.test_request_context('/test', environ_base={'REMOTE_ADDR': remote_addr}):
                ip = get_client_ip(request)
                assert ip == expected
