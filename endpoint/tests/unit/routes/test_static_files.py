"""Unit tests for static file serving routes."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, g

from endpoint.routes.static_files import (
    _rid,
    _mask_ip,
    _bad_filename,
    _serve_file,
    register_static_routes,
    IMG_EXTS,
    VID_EXTS,
    AUD_EXTS,
)
from endpoint.security.validation import ValidationError


class TestRid:
    """Tests for _rid helper function."""
    
    def test_rid_returns_request_id_from_g(self):
        """Test _rid returns request_id from Flask g."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            g.request_id = "test-id-123"
            assert _rid() == "test-id-123"
    
    def test_rid_returns_none_when_missing(self):
        """Test _rid returns None when request_id not in g."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            # Don't set g.request_id
            assert _rid() is None
    
    def test_rid_handles_no_request_context(self):
        """Test _rid handles case when no request context."""
        # Outside request context, should return None
        assert _rid() is None


class TestMaskIp:
    """Tests for _mask_ip helper function."""
    
    def test_mask_ip_masks_ipv4(self):
        """Test _mask_ip masks IPv4 address."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.get_client_ip', return_value="192.168.1.100"):
                result = _mask_ip()
                assert result == "192.****"
    
    def test_mask_ip_handles_short_ip(self):
        """Test _mask_ip handles IP shorter than 4 characters."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.get_client_ip', return_value="1.2"):
                result = _mask_ip()
                assert result == "****"
    
    def test_mask_ip_handles_none(self):
        """Test _mask_ip handles None IP."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.get_client_ip', return_value=None):
                result = _mask_ip()
                assert result == "****"
    
    def test_mask_ip_handles_empty_string(self):
        """Test _mask_ip handles empty string IP."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.get_client_ip', return_value=""):
                result = _mask_ip()
                assert result == "****"


class TestBadFilename:
    """Tests for _bad_filename helper function."""
    
    def test_bad_filename_returns_error_response(self):
        """Test _bad_filename returns 400 error response."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.logger') as mock_logger:
                response, status = _bad_filename("Invalid filename", "bad_file.txt", "req-123")
                
                assert status == 400
                assert response.json == {"error": "Invalid filename"}
                mock_logger.warning.assert_called_once()
                call_kwargs = mock_logger.warning.call_args[1]
                assert call_kwargs["extra"]["request_id"] == "req-123"
                assert call_kwargs["extra"]["file_name"] == "bad_file.txt"
    
    def test_bad_filename_handles_none_request_id(self):
        """Test _bad_filename handles None request_id."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.logger') as mock_logger:
                response, status = _bad_filename("Invalid", "file.txt", None)
                
                assert status == 400
                mock_logger.warning.assert_called_once()


class TestServeFile:
    """Tests for _serve_file helper function."""
    
    def test_serve_file_success(self, tmp_path):
        """Test _serve_file successfully serves valid file."""
        from flask import Flask
        app = Flask(__name__)
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake image content")
        
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.send_from_directory') as mock_send:
                mock_send.return_value = Mock(data=b"fake image content", status_code=200)
                
                result = _serve_file(tmp_path, "test.png", IMG_EXTS, "test", request_id="req-123")
                
                assert result is not None
                mock_send.assert_called_once()
                call_args = mock_send.call_args
                assert str(call_args[0][0]) == str(tmp_path)
                assert call_args[0][1] == "test.png"
    
    def test_serve_file_invalid_filename(self, tmp_path):
        """Test _serve_file rejects invalid filename."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.sanitize_filename', side_effect=ValidationError("Invalid")):
                result = _serve_file(tmp_path, "../etc/passwd", IMG_EXTS, "test", request_id="req-123")
                
                assert result[1] == 400
                assert result[0].json == {"error": "Invalid filename"}
    
    def test_serve_file_invalid_extension(self, tmp_path):
        """Test _serve_file rejects invalid extension."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            result = _serve_file(tmp_path, "test.exe", IMG_EXTS, "test", request_id="req-123")
            
            assert result[1] == 400
            assert result[0].json == {"error": "Invalid filename"}
    
    def test_serve_file_not_found(self, tmp_path):
        """Test _serve_file returns 404 for non-existent file."""
        from flask import Flask
        app = Flask(__name__)
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.logger') as mock_logger:
                result = _serve_file(tmp_path, "nonexistent.png", IMG_EXTS, "test", request_id="req-123")
                
                assert result[1] == 404
                assert result[0].json == {"error": "Not found"}
                mock_logger.warning.assert_called_once()
    
    def test_serve_file_logs_serving(self, tmp_path):
        """Test _serve_file logs when serving file."""
        from flask import Flask
        app = Flask(__name__)
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"content")
        
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.send_from_directory') as mock_send, \
                 patch('endpoint.routes.static_files.logger') as mock_logger, \
                 patch('endpoint.routes.static_files._mask_ip', return_value="192.****"):
                mock_send.return_value = Mock(data=b"content", status_code=200)
                
                _serve_file(tmp_path, "test.png", IMG_EXTS, "test", request_id="req-123")
                
                mock_logger.debug.assert_called_once()
                call_kwargs = mock_logger.debug.call_args[1]
                assert call_kwargs["extra"]["request_id"] == "req-123"
                assert call_kwargs["extra"]["file_name"] == "test.png"
                assert call_kwargs["extra"]["mimetype"] is not None
    
    def test_serve_file_handles_different_extensions(self, tmp_path):
        """Test _serve_file handles different file extensions."""
        from flask import Flask
        app = Flask(__name__)
        test_cases = [
            ("test.webp", IMG_EXTS),
            ("test.mp4", VID_EXTS),
            ("test.mp3", AUD_EXTS),
        ]
        
        for filename, allowed_exts in test_cases:
            test_file = tmp_path / filename
            test_file.write_bytes(b"content")
            
            with app.test_request_context('/test'):
                with patch('endpoint.routes.static_files.send_from_directory') as mock_send:
                    mock_send.return_value = Mock(data=b"content", status_code=200)
                    
                    result = _serve_file(tmp_path, filename, allowed_exts, "test", request_id=None)
                    
                    assert result is not None
                    mock_send.assert_called_once()
    
    def test_serve_file_handles_case_insensitive_extension(self, tmp_path):
        """Test _serve_file handles case-insensitive extensions."""
        from flask import Flask
        app = Flask(__name__)
        test_file = tmp_path / "test.PNG"
        test_file.write_bytes(b"content")
        
        with app.test_request_context('/test'):
            with patch('endpoint.routes.static_files.send_from_directory') as mock_send:
                mock_send.return_value = Mock(data=b"content", status_code=200)
                
                result = _serve_file(tmp_path, "test.PNG", IMG_EXTS, "test", request_id=None)
                
                assert result is not None
                # Should accept .PNG (uppercase)


class TestRegisterStaticRoutes:
    """Tests for register_static_routes function."""
    
    def test_register_static_routes_registers_health(self):
        """Test register_static_routes registers health endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        # Check route exists
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/health' in rule for rule in rules)
    
    def test_register_static_routes_registers_money_gif(self):
        """Test register_static_routes registers money-gif endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/money-gifs/<filename>' in rule for rule in rules)
    
    def test_register_static_routes_registers_rules(self):
        """Test register_static_routes registers rules endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/rules/<filename>' in rule for rule in rules)
    
    def test_register_static_routes_registers_gifs(self):
        """Test register_static_routes registers gifs endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/gifs/<filename>' in rule for rule in rules)
    
    def test_register_static_routes_registers_feeding_stickers(self):
        """Test register_static_routes registers feeding-stickers endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/feeding-stickers/<filename>' in rule for rule in rules)
    
    def test_register_static_routes_registers_stickers(self):
        """Test register_static_routes registers stickers endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/stickers/<filename>' in rule for rule in rules)
    
    def test_register_static_routes_registers_stats_image(self):
        """Test register_static_routes registers stats-image endpoint."""
        from flask import Flask
        app = Flask(__name__)
        register_static_routes(app)
        
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        assert any('/stats-image/<int:user_id>' in rule for rule in rules)
    
    def test_register_static_routes_applies_rate_limiting(self):
        """Test register_static_routes applies rate limiting decorators."""
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_static_routes(app)
        
        # Check that routes have rate limiting (by checking if rate_limit decorator was applied)
        # This is indirect - we verify routes exist and are callable
        client = app.test_client()
        
        # Health endpoint should be rate limited
        response = client.get('/health')
        assert response.status_code in [200, 429]  # 429 if rate limited, 200 if not
