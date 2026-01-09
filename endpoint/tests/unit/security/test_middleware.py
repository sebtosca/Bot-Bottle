"""Unit tests for security middleware."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, request, Response
from endpoint.security.middleware import (
    setup_security_headers,
    setup_proxy_fix,
    get_client_ip,
    rate_limit,
)
from endpoint.security.rate_limiter import InMemoryRateLimiter, RateLimiter, get_rate_limiter
from endpoint.security.middleware import mask_identifier


class TestSetupSecurityHeaders:
    """Tests for setup_security_headers function."""
    
    def test_security_headers_added_to_response(self, app, client):
        """Test security headers are added to all responses."""
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
        assert "style-src 'none'" in csp
    
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
        """Test HSTS header is added on HTTPS requests."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Use url_scheme parameter to simulate HTTPS request
        response = client.get('/test', url_scheme='https')
        
        assert 'Strict-Transport-Security' in response.headers
        assert 'max-age=31536000' in response.headers.get('Strict-Transport-Security')
        assert 'includeSubDomains' in response.headers.get('Strict-Transport-Security')
    
    def test_security_headers_preserve_existing_headers(self, app, client):
        """Test security headers don't override existing headers."""
        setup_security_headers(app)
        
        @app.route('/test')
        def test_route():
            resp = Response('{"status": "ok"}', mimetype='application/json')
            resp.headers['X-Content-Type-Options'] = 'custom-value'
            return resp
        
        response = client.get('/test')
        
        # Should preserve existing header
        assert response.headers.get('X-Content-Type-Options') == 'custom-value'
    
    def test_security_headers_on_error_responses(self, app, client):
        """Test security headers are added to error responses."""
        setup_security_headers(app)
        
        @app.route('/error')
        def error_route():
            return {"error": "not found"}, 404
        
        response = client.get('/error')
        
        assert response.status_code == 404
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'


class TestSetupProxyFix:
    """Tests for setup_proxy_fix function."""
    
    def test_proxy_fix_applied(self, app):
        """Test ProxyFix is applied to WSGI app."""
        original_wsgi_app = app.wsgi_app
        
        setup_proxy_fix(app, x_for=1, x_proto=1)
        
        # WSGI app should be wrapped
        assert app.wsgi_app != original_wsgi_app
        assert hasattr(app.wsgi_app, '__call__')
    
    def test_proxy_fix_with_custom_params(self, app):
        """Test ProxyFix with custom x_for and x_proto values."""
        setup_proxy_fix(app, x_for=2, x_proto=2)
        
        # Should not raise
        assert app.wsgi_app is not None


class TestGetClientIP:
    """Tests for get_client_ip function."""
    
    def test_get_client_ip_from_remote_addr(self, app):
        """Test getting IP from remote_addr."""
        with app.test_request_context('/test', environ_base={'REMOTE_ADDR': '192.168.1.1'}):
            ip = get_client_ip(request)
            assert ip == '192.168.1.1'
    
    def test_get_client_ip_handles_none(self, app):
        """Test get_client_ip handles None remote_addr."""
        with app.test_request_context('/test', environ_base={'REMOTE_ADDR': None}):
            ip = get_client_ip(request)
            assert ip == "unknown"
    
    def test_get_client_ip_handles_missing_remote_addr(self, app):
        """Test get_client_ip handles missing remote_addr."""
        with app.test_request_context('/test'):
            # Remove REMOTE_ADDR if it exists
            if hasattr(request, 'environ'):
                request.environ.pop('REMOTE_ADDR', None)
            ip = get_client_ip(request)
            assert ip == "unknown"
    
    def test_get_client_ip_with_custom_request(self, app):
        """Test get_client_ip with custom request object."""
        mock_request = Mock()
        mock_request.remote_addr = '10.0.0.1'
        
        ip = get_client_ip(mock_request)
        assert ip == '10.0.0.1'


class TestRateLimit:
    """Tests for rate_limit decorator."""
    
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
    
    def test_rate_limit_uses_default_limiter(self, app):
        """Test rate limit uses default limiter when not provided."""
        with patch('endpoint.security.middleware.get_rate_limiter') as mock_get:
            mock_limiter = MagicMock(spec=RateLimiter)
            mock_limiter.allow_and_record.return_value = (True, None)
            mock_get.return_value = mock_limiter
            
            @app.route('/test')
            @rate_limit(max_requests=10, window_seconds=60)
            def test_route():
                return {"status": "ok"}
            
            client = app.test_client()
            response = client.get('/test')
            
            assert response.status_code == 200
            mock_get.assert_called_once()
            mock_limiter.allow_and_record.assert_called_once()
    
    def test_rate_limit_with_custom_identifier_func(self, app, rate_limiter):
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
        
        # User 1 makes 2 requests
        for _ in range(2):
            response = client.get('/test', headers={'X-User-ID': 'user1'})
            assert response.status_code == 200
        
        # User 1's 3rd request should be blocked
        response = client.get('/test', headers={'X-User-ID': 'user1'})
        assert response.status_code == 429
        
        # User 2 should still be allowed
        response = client.get('/test', headers={'X-User-ID': 'user2'})
        assert response.status_code == 200
    
    def test_rate_limit_logs_warning_on_exceed(self, app, rate_limiter):
        """Test rate limit logs warning when limit exceeded."""
        with patch('endpoint.security.middleware.logger') as mock_logger:
            @app.route('/test')
            @rate_limit(max_requests=1, window_seconds=60, rate_limiter=rate_limiter)
            def test_route():
                return {"status": "ok"}
            
            client = app.test_client()
            
            # First request allowed
            client.get('/test')
            
            # Second request blocked
            client.get('/test')
            
            # Should log warning
            assert mock_logger.warning.called
            call_args = mock_logger.warning.call_args
            assert call_args[0][0] == "Rate limit exceeded"
            assert "identifier" in call_args[1]["extra"]
            assert "endpoint" in call_args[1]["extra"]
            assert "retry_after" in call_args[1]["extra"]
    
    def test_rate_limit_masks_identifier_in_logs(self, app, rate_limiter):
        """Test rate limit masks identifier in logs."""
        with patch('endpoint.security.middleware.logger') as mock_logger:
            @app.route('/test')
            @rate_limit(max_requests=1, window_seconds=60, rate_limiter=rate_limiter)
            def test_route():
                return {"status": "ok"}
            
            client = app.test_client()
            
            # Make requests from specific IP
            client.get('/test', environ_base={'REMOTE_ADDR': '192.168.1.100'})
            client.get('/test', environ_base={'REMOTE_ADDR': '192.168.1.100'})
            
            # Check that identifier is masked in logs
            call_args = mock_logger.warning.call_args
            masked_id = call_args[1]["extra"]["identifier"]
            assert masked_id.endswith("****")
            assert len(masked_id) == 8  # 4 chars + "****"
    
    def test_rate_limit_short_identifier_masking(self, app, rate_limiter):
        """Test rate limit masks short identifiers correctly."""
        with patch('endpoint.security.middleware.logger') as mock_logger:
            @app.route('/test')
            @rate_limit(max_requests=1, window_seconds=60, rate_limiter=rate_limiter)
            def test_route():
                return {"status": "ok"}
            
            client = app.test_client()
            
            # Make requests with short IP
            client.get('/test', environ_base={'REMOTE_ADDR': '1.2.3'})
            client.get('/test', environ_base={'REMOTE_ADDR': '1.2.3'})
            
            # Short identifier should be fully masked
            call_args = mock_logger.warning.call_args
            masked_id = call_args[1]["extra"]["identifier"]
            assert masked_id == "****"
    
    def test_rate_limit_records_request_on_success(self, app, rate_limiter):
        """Test rate limit records request when allowed."""
        @app.route('/test')
        @rate_limit(max_requests=10, window_seconds=60, rate_limiter=rate_limiter)
        def test_route():
            return {"status": "ok"}
        
        client = app.test_client()
        
        # Make a request
        response = client.get('/test')
        assert response.status_code == 200
        
        # Check that request was recorded (by making max requests)
        for _ in range(9):  # 9 more to reach 10
            response = client.get('/test')
            assert response.status_code == 200
        
        # 11th should be blocked
        response = client.get('/test')
        assert response.status_code == 429
    
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
        assert "message" in data
        assert "Too many requests" in data["message"]
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"].isdigit()


class TestMaskIdentifier:
    """Tests for mask_identifier helper function."""
    
    def test_mask_identifier_long_string(self):
        """Test masking long identifiers."""
        assert mask_identifier("192.168.1.100") == "192.****"
        assert mask_identifier("user-12345") == "user****"
        assert len(mask_identifier("192.168.1.100")) == 8
    
    def test_mask_identifier_short_string(self):
        """Test masking short identifiers."""
        assert mask_identifier("1.2.3") == "****"
        assert mask_identifier("abc") == "****"
        assert mask_identifier("") == "****"
    
    def test_mask_identifier_exactly_five_chars(self):
        """Test masking identifier with exactly 5 characters."""
        assert mask_identifier("12345") == "****"
    
    def test_mask_identifier_six_chars(self):
        """Test masking identifier with 6 characters."""
        assert mask_identifier("123456") == "1234****"
        assert len(mask_identifier("123456")) == 8


class TestGetRateLimiter:
    """Tests for get_rate_limiter factory function."""
    
    def test_get_rate_limiter_without_redis_url(self):
        """Test get_rate_limiter returns in-memory when no Redis URL."""
        limiter = get_rate_limiter()
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_get_rate_limiter_with_invalid_redis_url(self):
        """Test get_rate_limiter falls back to in-memory with invalid Redis URL."""
        limiter = get_rate_limiter(redis_url="redis://invalid:6379")
        assert isinstance(limiter, InMemoryRateLimiter)
    
    def test_get_rate_limiter_with_none_redis_url(self):
        """Test get_rate_limiter with explicit None."""
        limiter = get_rate_limiter(redis_url=None)
        assert isinstance(limiter, InMemoryRateLimiter)
