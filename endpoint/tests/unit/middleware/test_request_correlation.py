"""Unit tests for request correlation middleware."""

import pytest
import uuid
import logging
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g, has_request_context
from endpoint.middleware.request_correlation import (
    setup_request_correlation,
    _record_factory,
    _DEFAULT_FACTORY
)


class TestRecordFactory:
    """Tests for _record_factory function."""
    
    def test_record_factory_adds_request_id_in_context(self, app):
        """Test record factory adds request_id when in request context."""
        with app.test_request_context('/test'):
            g.request_id = "test-request-123"
            
            # Mock the default factory
            mock_record = Mock()
            mock_record.request_id = None
            with patch('endpoint.middleware.request_correlation._DEFAULT_FACTORY', return_value=mock_record):
                record = _record_factory('name', 'level', 'pathname', 'lineno', 'msg', (), {})
            
            assert record.request_id == "test-request-123"
    
    def test_record_factory_handles_no_context(self):
        """Test record factory handles logging outside request context."""
        # Mock the default factory
        mock_record = Mock()
        mock_record.request_id = None
        with patch('endpoint.middleware.request_correlation._DEFAULT_FACTORY', return_value=mock_record):
            # Mock has_request_context to return False
            with patch('endpoint.middleware.request_correlation.has_request_context', return_value=False):
                record = _record_factory('name', 'level', 'pathname', 'lineno', 'msg', (), {})
        
        assert record.request_id is None
    
    def test_record_factory_handles_missing_request_id(self, app):
        """Test record factory handles missing request_id in g."""
        with app.test_request_context('/test'):
            # Don't set g.request_id
            mock_record = Mock()
            mock_record.request_id = None
            with patch('endpoint.middleware.request_correlation._DEFAULT_FACTORY', return_value=mock_record):
                record = _record_factory('name', 'level', 'pathname', 'lineno', 'msg', (), {})
        
        assert record.request_id is None
    
    def test_record_factory_preserves_other_record_attributes(self, app):
        """Test record factory preserves other log record attributes."""
        with app.test_request_context('/test'):
            g.request_id = "test-request-123"
            
            mock_record = Mock()
            mock_record.request_id = None
            mock_record.name = "test_logger"
            mock_record.levelname = "INFO"
            with patch('endpoint.middleware.request_correlation._DEFAULT_FACTORY', return_value=mock_record):
                record = _record_factory('name', 'level', 'pathname', 'lineno', 'msg', (), {})
            
            assert record.request_id == "test-request-123"
            assert record.name == "test_logger"
            assert record.levelname == "INFO"


class TestSetupRequestCorrelation:
    """Tests for setup_request_correlation function."""
    
    def test_setup_adds_request_id_middleware(self, app, client):
        """Test setup adds request ID middleware."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            assert hasattr(g, 'request_id')
            assert g.request_id is not None
            return {"status": "ok"}
        
        response = client.get('/test')
        assert response.status_code == 200
    
    def test_setup_uses_existing_request_id_header(self, app, client):
        """Test setup uses X-Request-ID header if present."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            assert g.request_id == 'custom-id-123'
            return {"status": "ok"}
        
        response = client.get('/test', headers={'X-Request-ID': 'custom-id-123'})
        assert response.status_code == 200
    
    def test_setup_generates_request_id_if_missing(self, app, client):
        """Test setup generates UUID if header missing."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            request_id = g.request_id
            assert request_id is not None
            # Should be valid UUID format
            uuid.UUID(request_id)  # Should not raise
            return {"status": "ok", "request_id": request_id}
        
        response = client.get('/test')
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] is not None
    
    def test_setup_rejects_too_long_request_id(self, app, client):
        """Test setup rejects request ID that's too long."""
        setup_request_correlation(app)
        
        long_id = "a" * 101
        
        @app.route('/test')
        def test_route():
            # Should generate new ID instead
            request_id = g.request_id
            assert request_id != long_id
            assert len(request_id) <= 100
            return {"status": "ok", "request_id": request_id}
        
        response = client.get('/test', headers={'X-Request-ID': long_id})
        assert response.status_code == 200
        data = response.get_json()
        assert data["request_id"] != long_id
        assert len(data["request_id"]) <= 100
    
    def test_setup_logs_request_start(self, app, client):
        """Test setup logs request start."""
        with patch('endpoint.middleware.request_correlation.logger') as mock_logger:
            setup_request_correlation(app)
            
            @app.route('/test')
            def test_route():
                # Request ID should be set
                assert hasattr(g, 'request_id')
                return {"status": "ok"}
            
            response = client.get('/test')
            assert response.status_code == 200
            # Verify logging was called
            assert mock_logger.info.called
            # Check that log call includes method and path
            call_args = mock_logger.info.call_args_list[0]
            assert call_args[0][0] == "Request started"
            assert "method" in call_args[1]["extra"]
            assert "path" in call_args[1]["extra"]
    
    def test_setup_logs_request_completion(self, app, client):
        """Test setup logs request completion."""
        with patch('endpoint.middleware.request_correlation.logger') as mock_logger:
            setup_request_correlation(app)
            
            @app.route('/test')
            def test_route():
                return {"status": "ok"}
            
            response = client.get('/test')
            assert response.status_code == 200
            # Verify completion logging was called
            assert mock_logger.info.call_count >= 2  # Start + completion
            # Check that completion log includes status_code
            completion_calls = [call for call in mock_logger.info.call_args_list 
                              if call[0][0] == "Request completed"]
            assert len(completion_calls) > 0
            assert "status_code" in completion_calls[0][1]["extra"]
    
    def test_setup_sets_log_record_factory(self, app):
        """Test setup sets the log record factory."""
        original_factory = logging.getLogRecordFactory()
        try:
            setup_request_correlation(app)
            # Factory should be set to _record_factory
            current_factory = logging.getLogRecordFactory()
            assert current_factory == _record_factory
        finally:
            logging.setLogRecordFactory(original_factory)
    
    def test_setup_adds_request_id_to_response_header(self, app, client):
        """Test setup adds request ID to response headers."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test')
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
        # Should be valid UUID format
        uuid.UUID(response.headers["X-Request-ID"])
    
    def test_setup_preserves_custom_request_id_in_response(self, app, client):
        """Test setup preserves custom request ID in response header."""
        setup_request_correlation(app)
        custom_id = "custom-request-id-123"
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test', headers={'X-Request-ID': custom_id})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id
    
    def test_setup_handles_empty_request_id_header(self, app, client):
        """Test setup handles empty request ID header."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            return {"status": "ok"}
        
        response = client.get('/test', headers={'X-Request-ID': ''})
        assert response.status_code == 200
        # Should generate a new UUID
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert request_id != ""
        uuid.UUID(request_id)  # Should be valid UUID
    
    def test_setup_handles_exactly_100_char_request_id(self, app, client):
        """Test setup accepts request ID that's exactly 100 characters."""
        setup_request_correlation(app)
        exactly_100_chars = "a" * 100
        
        @app.route('/test')
        def test_route():
            assert g.request_id == exactly_100_chars
            return {"status": "ok"}
        
        response = client.get('/test', headers={'X-Request-ID': exactly_100_chars})
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == exactly_100_chars
    
    def test_setup_handles_none_request_id_header(self, app, client):
        """Test setup handles None request ID header value."""
        setup_request_correlation(app)
        
        @app.route('/test')
        def test_route():
            # Should generate a UUID
            assert g.request_id is not None
            uuid.UUID(g.request_id)  # Should be valid UUID
            return {"status": "ok"}
        
        # Simulate None header by not providing it
        response = client.get('/test')
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        uuid.UUID(response.headers["X-Request-ID"])  # Should be valid UUID
    
    def test_record_factory_calls_default_factory(self, app):
        """Test that record factory actually calls the default factory."""
        with app.test_request_context('/test'):
            g.request_id = "test-123"
            
            # Use real factory, not mocked
            record = _record_factory(
                'test_logger',
                logging.INFO,
                'test.py',
                42,
                'Test message',
                (),
                {}
            )
            
            # Should have request_id
            assert record.request_id == "test-123"
            # Should have standard log record attributes
            assert record.name == 'test_logger'
            assert record.levelno == logging.INFO
            assert record.pathname == 'test.py'
            assert record.lineno == 42
            assert record.msg == 'Test message'
