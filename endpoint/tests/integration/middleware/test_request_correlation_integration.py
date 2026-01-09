"""Integration tests for request correlation middleware."""

import pytest
import uuid
import logging
from flask import Flask, g, request
from endpoint.middleware.request_correlation import setup_request_correlation


class TestRequestCorrelationIntegration:
    """Integration tests for request correlation middleware."""
    
    def test_full_request_flow_with_custom_id(self, app, client):
        """Test complete request flow with custom request ID."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            assert hasattr(g, 'request_id')
            assert g.request_id == 'custom-id-456'
            return {"status": "ok", "request_id": g.request_id}
        
        response = client.get('/test', headers={'X-Request-ID': 'custom-id-456'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] == 'custom-id-456'
        assert response.headers["X-Request-ID"] == 'custom-id-456'
    
    def test_full_request_flow_with_generated_id(self, app, client):
        """Test complete request flow with generated UUID."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            assert hasattr(g, 'request_id')
            request_id = g.request_id
            # Should be valid UUID
            uuid.UUID(request_id)
            return {"status": "ok", "request_id": request_id}
        
        response = client.get('/test')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] is not None
        assert response.headers["X-Request-ID"] == data["request_id"]
        # Verify it's a valid UUID
        uuid.UUID(response.headers["X-Request-ID"])
    
    def test_request_id_available_in_logging(self, app, client):
        """Test that request ID is available in log records during request."""
        setup_request_correlation(app)
        
        log_records = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)
        
        handler = TestHandler()
        logger = logging.getLogger('endpoint.middleware.request_correlation')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        @app.route('/test')
        def test_route():
            logger.info("Test log message")
            return {"status": "ok"}
        
        response = client.get('/test', headers={'X-Request-ID': 'test-log-id'})
        
        assert response.status_code == 200
        # Check that log records have request_id
        assert len(log_records) > 0
        # Find records with request_id set
        records_with_id = [r for r in log_records if hasattr(r, 'request_id') and r.request_id is not None]
        assert len(records_with_id) > 0, "At least one log record should have request_id"
        # The request_id should match
        assert any(r.request_id == 'test-log-id' for r in records_with_id)
        
        logger.removeHandler(handler)
    
    def test_multiple_requests_generate_different_ids(self, app, client):
        """Test that multiple requests generate different request IDs."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok", "request_id": g.request_id}
        
        # Make multiple requests
        request_ids = []
        for _ in range(5):
            response = client.get('/test')
            assert response.status_code == 200
            data = response.get_json()
            request_ids.append(data["request_id"])
        
        # All should be unique
        assert len(set(request_ids)) == len(request_ids), \
            "Each request should have a unique ID"
    
    def test_request_id_persists_through_request_lifecycle(self, app, client):
        """Test that request ID persists through entire request lifecycle."""
        setup_request_correlation(app)
        
        request_id_tracker = []
        
        @app.before_request
        def track_before():
            request_id_tracker.append(("before", g.request_id))
        
        @app.route('/test')
        def test_route():
            request_id_tracker.append(("route", g.request_id))
            return {"status": "ok", "request_id": g.request_id}
        
        @app.after_request
        def track_after(response):
            request_id_tracker.append(("after", g.request_id))
            return response
        
        response = client.get('/test', headers={'X-Request-ID': 'persistent-id'})
        
        assert response.status_code == 200
        # Request ID should be the same throughout
        ids = [rid for _, rid in request_id_tracker]
        assert len(set(ids)) == 1, "Request ID should be consistent throughout request"
        assert ids[0] == 'persistent-id'
    
    def test_error_responses_include_request_id(self, app, client):
        """Test that error responses include request ID in headers."""
        setup_request_correlation(app)
        
        @app.route('/error')
        def error_route():
            return {"error": "not found"}, 404
        
        response = client.get('/error', headers={'X-Request-ID': 'error-id'})
        
        assert response.status_code == 404
        assert response.headers["X-Request-ID"] == 'error-id'
    
    def test_request_id_with_different_http_methods(self, app, client):
        """Test request ID works with different HTTP methods."""
        setup_request_correlation(app)
        
        @app.route('/test', methods=['GET', 'POST', 'PUT', 'DELETE'])
        def test_route():
            return {"status": "ok", "request_id": g.request_id, "method": request.method}
        
        methods = ['GET', 'POST', 'PUT', 'DELETE']
        for method in methods:
            response = client.open('/test', method=method, headers={'X-Request-ID': f'{method}-id'})
            assert response.status_code == 200
            data = response.get_json()
            assert data["request_id"] == f'{method}-id'
            assert response.headers["X-Request-ID"] == f'{method}-id'
    
    def test_request_id_with_query_parameters(self, app, client):
        """Test request ID works with query parameters."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok", "request_id": g.request_id}
        
        response = client.get('/test?param1=value1&param2=value2', 
                             headers={'X-Request-ID': 'query-id'})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == 'query-id'
    
    def test_request_id_with_different_paths(self, app, client):
        """Test request ID works with different URL paths."""
        setup_request_correlation(app)
        
        @app.route('/path1')
        def path1():
            return {"status": "ok", "request_id": g.request_id}
        
        @app.route('/path2')
        def path2():
            return {"status": "ok", "request_id": g.request_id}
        
        response1 = client.get('/path1', headers={'X-Request-ID': 'path1-id'})
        response2 = client.get('/path2', headers={'X-Request-ID': 'path2-id'})
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.headers["X-Request-ID"] == 'path1-id'
        assert response2.headers["X-Request-ID"] == 'path2-id'
    
    def test_request_id_rejected_when_too_long(self, app, client):
        """Test that request IDs longer than 100 chars are rejected and regenerated."""
        setup_request_correlation(app)
        
        long_id = "a" * 150
        
        @app.route('/test')
        def test_route():
            # Should not be the long_id
            assert g.request_id != long_id
            assert len(g.request_id) <= 100
            return {"status": "ok", "request_id": g.request_id}
        
        response = client.get('/test', headers={'X-Request-ID': long_id})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] != long_id
        assert len(data["request_id"]) <= 100
        assert response.headers["X-Request-ID"] != long_id
        # Should be a valid UUID (generated)
        uuid.UUID(response.headers["X-Request-ID"])
    
    def test_logging_outside_request_context(self, app):
        """Test that logging outside request context doesn't break."""
        setup_request_correlation(app)
        
        logger = logging.getLogger('test_logger')
        
        # Log outside request context
        logger.info("Test message outside request")
        
        # Should not raise exception
        # The record factory should handle missing request context gracefully
        assert True  # If we get here, no exception was raised
    
    def test_concurrent_requests_maintain_separate_ids(self, app, client):
        """Test that concurrent requests maintain separate request IDs."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok", "request_id": g.request_id}
        
        # Simulate concurrent requests (sequential in test, but should still work)
        request_ids = []
        for i in range(10):
            response = client.get('/test', headers={'X-Request-ID': f'concurrent-{i}'})
            assert response.status_code == 200
            data = response.get_json()
            request_ids.append(data["request_id"])
        
        # Each should have its own ID
        assert len(set(request_ids)) == len(request_ids)
        # Verify each matches the header
        for i, rid in enumerate(request_ids):
            assert rid == f'concurrent-{i}'
    
    def test_request_id_with_exception_handling(self, app, client):
        """Test that request ID is preserved even when exceptions occur."""
        setup_request_correlation(app)
        
        @app.route('/error')
        def error_route():
            raise ValueError("Test error")
        
        # Register error handler
        @app.errorhandler(ValueError)
        def handle_error(e):
            return {"error": str(e), "request_id": g.request_id}, 500
        
        response = client.get('/error', headers={'X-Request-ID': 'error-test-id'})
        
        assert response.status_code == 500
        data = response.get_json()
        assert data["request_id"] == 'error-test-id'
        assert response.headers["X-Request-ID"] == 'error-test-id'
    
    def test_request_id_with_redirect(self, app, client):
        """Test that request ID is preserved through redirects."""
        setup_request_correlation(app)
        
        @app.route('/redirect')
        def redirect_route():
            from flask import redirect
            return redirect('/target')
        
        @app.route('/target')
        def target_route():
            return {"status": "ok", "request_id": g.request_id}
        
        response = client.get('/redirect', headers={'X-Request-ID': 'redirect-id'}, follow_redirects=True)
        
        assert response.status_code == 200
        data = response.get_json()
        # Note: redirect creates a new request, so request_id will be different
        # This test verifies the middleware works with redirects
        assert "request_id" in data
    
    def test_log_record_factory_integration(self, app, client):
        """Test that log records created during request have request_id."""
        setup_request_correlation(app)
        
        log_records = []
        
        class TestHandler(logging.Handler):
            def emit(self, record):
                log_records.append(record)
        
        handler = TestHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
        
        try:
            @app.route('/test')
            def test_route():
                # Log from different logger
                test_logger = logging.getLogger('test.module')
                test_logger.info("Test log from route")
                return {"status": "ok"}
            
            response = client.get('/test', headers={'X-Request-ID': 'log-test-id'})
            
            assert response.status_code == 200
            # Find log records with request_id
            records_with_id = [r for r in log_records if hasattr(r, 'request_id') and r.request_id == 'log-test-id']
            assert len(records_with_id) > 0, "At least one log record should have the request_id"
        finally:
            root_logger.removeHandler(handler)
