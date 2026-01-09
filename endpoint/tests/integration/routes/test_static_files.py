"""Integration tests for static file serving routes."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from flask import Flask, g
from endpoint.routes.static_files import (
    register_static_routes,
    MONEY_GIF_DIR,
    RULES_DIR,
    PROJECT_ROOT,
)
from endpoint.middleware.request_correlation import setup_request_correlation


class TestStaticFileRoutes:
    """Integration tests for static file routes."""
    
    @pytest.fixture
    def app_with_routes(self):
        """Create Flask app with static routes registered."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        setup_request_correlation(app)  # Setup request correlation to enable request_id
        register_static_routes(app)
        return app
    
    def test_health_endpoint(self, app_with_routes):
        """Test health check endpoint."""
        client = app_with_routes.test_client()
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
    
    def test_serve_money_gif_success(self, app_with_routes, project_root_path):
        """Test serving money GIF file successfully."""
        money_gif_dir = project_root_path / "money_GIF"
        money_gif_dir.mkdir(exist_ok=True)
        test_gif = money_gif_dir / "test_money.gif"
        test_gif.write_bytes(b"fake gif content")
        
        try:
            client = app_with_routes.test_client()
            response = client.get('/money-gifs/test_money.gif')
            
            assert response.status_code == 200
            assert response.data == b"fake gif content"
        finally:
            if test_gif.exists():
                test_gif.unlink()
    
    def test_serve_money_gif_not_found(self, app_with_routes):
        """Test serving non-existent money GIF."""
        client = app_with_routes.test_client()
        response = client.get('/money-gifs/nonexistent.gif')
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
    
    def test_serve_money_gif_invalid_extension(self, app_with_routes):
        """Test money GIF endpoint rejects invalid extension."""
        client = app_with_routes.test_client()
        response = client.get('/money-gifs/test.exe')
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_serve_rules_success(self, app_with_routes, project_root_path):
        """Test serving rules image file successfully."""
        rules_dir = project_root_path / "Rule"
        rules_dir.mkdir(exist_ok=True)
        test_image = rules_dir / "test_rule.png"
        test_image.write_bytes(b"fake png content")
        
        try:
            client = app_with_routes.test_client()
            response = client.get('/rules/test_rule.png')
            
            assert response.status_code == 200
            assert response.data == b"fake png content"
        finally:
            if test_image.exists():
                test_image.unlink()
    
    def test_serve_rules_not_found(self, app_with_routes):
        """Test serving non-existent rules image."""
        client = app_with_routes.test_client()
        response = client.get('/rules/nonexistent.png')
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
    
    def test_serve_gif_with_character_id(self, app_with_routes, project_root_path):
        """Test serving GIF with character_id parameter."""
        with patch('endpoint.routes.static_files.get_character_config') as mock_config:
            mock_config.return_value = {"gif_dir": "test_gif_dir"}
            gif_dir = project_root_path / "test_gif_dir"
            gif_dir.mkdir(exist_ok=True)
            test_gif = gif_dir / "test.gif"
            test_gif.write_bytes(b"fake gif")
            
            try:
                client = app_with_routes.test_client()
                response = client.get('/gifs/test.gif?character_id=00001')
                
                assert response.status_code == 200
                assert response.data == b"fake gif"
            finally:
                if test_gif.exists():
                    test_gif.unlink()
    
    def test_serve_gif_fallback(self, app_with_routes, project_root_path):
        """Test GIF serving falls back when primary directory not found."""
        with patch('endpoint.routes.static_files.get_character_config') as mock_config:
            mock_config.return_value = {"gif_dir": "nonexistent_dir"}
            # Create fallback directory
            fallback_dir = project_root_path / "Cherry_GIF"
            fallback_dir.mkdir(exist_ok=True)
            test_gif = fallback_dir / "test.gif"
            test_gif.write_bytes(b"fallback gif")
            
            try:
                client = app_with_routes.test_client()
                response = client.get('/gifs/test.gif?character_id=00002')
                
                assert response.status_code == 200
                assert response.data == b"fallback gif"
            finally:
                if test_gif.exists():
                    test_gif.unlink()
    
    def test_serve_gif_invalid_character_id(self, app_with_routes):
        """Test GIF serving handles invalid character_id."""
        with patch('endpoint.routes.static_files.get_character_config') as mock_config:
            mock_config.return_value = {"gif_dir": "default_dir"}
            client = app_with_routes.test_client()
            response = client.get('/gifs/test.gif?character_id=invalid')
            
            # Should default to 00001
            assert response.status_code in [200, 404]  # 404 if file doesn't exist
    
    def test_serve_feeding_sticker_success(self, app_with_routes, project_root_path):
        """Test serving feeding sticker successfully."""
        with patch('endpoint.routes.static_files.get_character_config') as mock_config:
            mock_config.return_value = {"feeding_sticker_dir": "test_sticker_dir"}
            sticker_dir = project_root_path / "test_sticker_dir"
            sticker_dir.mkdir(exist_ok=True)
            test_sticker = sticker_dir / "test.webp"
            test_sticker.write_bytes(b"fake webp")
            
            try:
                client = app_with_routes.test_client()
                response = client.get('/feeding-stickers/test.webp?character_id=00001')
                
                assert response.status_code == 200
                assert response.data == b"fake webp"
            finally:
                if test_sticker.exists():
                    test_sticker.unlink()
    
    def test_serve_feeding_sticker_fallback(self, app_with_routes, project_root_path):
        """Test feeding sticker falls back when primary directory not found."""
        with patch('endpoint.routes.static_files.get_character_config') as mock_config:
            mock_config.return_value = {"feeding_sticker_dir": "nonexistent"}
            # For character_id=00001, fallback is Pompon_normand_feeding_game_logic_stickers
            # For character_id=00002, fallback is feeding_game_logic_stickers
            fallback_dir = project_root_path / "Pompon_normand_feeding_game_logic_stickers"
            fallback_dir.mkdir(exist_ok=True)
            test_sticker = fallback_dir / "test.webp"
            test_sticker.write_bytes(b"fallback webp")
            
            try:
                client = app_with_routes.test_client()
                response = client.get('/feeding-stickers/test.webp?character_id=00001')
                
                assert response.status_code == 200
                assert response.data == b"fallback webp"
            finally:
                if test_sticker.exists():
                    test_sticker.unlink()
    
    def test_serve_sticker_success(self, app_with_routes, project_root_path):
        """Test serving sticker file successfully."""
        stickers_dir = project_root_path / "stickers"
        stickers_dir.mkdir(exist_ok=True)
        test_sticker = stickers_dir / "test_sticker.webp"
        test_sticker.write_bytes(b"fake webp content")
        
        try:
            client = app_with_routes.test_client()
            response = client.get('/stickers/test_sticker.webp')
            
            assert response.status_code == 200
            assert response.data == b"fake webp content"
            assert response.content_type == "image/webp"
        finally:
            if test_sticker.exists():
                test_sticker.unlink()
    
    def test_serve_sticker_bouteille_affamee(self, app_with_routes, project_root_path):
        """Test serving bouteille_affamee sticker from correct directory."""
        feeding_dir = project_root_path / "feeding_game_logic_stickers"
        feeding_dir.mkdir(exist_ok=True)
        test_sticker = feeding_dir / "bouteille_affamee.webp"
        test_sticker.write_bytes(b"hungry bottle")
        
        try:
            client = app_with_routes.test_client()
            response = client.get('/stickers/bouteille_affamee.webp')
            
            assert response.status_code == 200
            assert response.data == b"hungry bottle"
        finally:
            if test_sticker.exists():
                test_sticker.unlink()
    
    def test_serve_sticker_cider(self, app_with_routes, project_root_path):
        """Test serving cider sticker from correct directory."""
        cider_dir = project_root_path / "Pompom_normand_emotional_sticker"
        cider_dir.mkdir(exist_ok=True)
        test_sticker = cider_dir / "cider.webp"
        test_sticker.write_bytes(b"cider sticker")
        
        try:
            client = app_with_routes.test_client()
            response = client.get('/stickers/cider.webp')
            
            assert response.status_code == 200
            assert response.data == b"cider sticker"
        finally:
            if test_sticker.exists():
                test_sticker.unlink()
    
    def test_serve_sticker_not_found(self, app_with_routes):
        """Test serving non-existent sticker."""
        client = app_with_routes.test_client()
        response = client.get('/stickers/nonexistent.webp')
        
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "Sticker not found" in data["error"]
    
    def test_serve_sticker_invalid_filename(self, app_with_routes):
        """Test serving sticker with invalid filename."""
        client = app_with_routes.test_client()
        response = client.get('/stickers/..%2F..%2F..%2Fetc%2Fpasswd')
        
        assert response.status_code in (400, 404)
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data
    
    def test_serve_sticker_invalid_extension(self, app_with_routes):
        """Test serving file with invalid extension."""
        client = app_with_routes.test_client()
        response = client.get('/stickers/test.exe')
        
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_serve_stats_image_success(self, app_with_routes):
        """Test serving stats image successfully."""
        with patch('endpoint.routes.static_files.is_db_initialized', return_value=True), \
             patch('endpoint.routes.static_files.get_session') as mock_session, \
             patch('endpoint.routes.static_files.get_user_stats') as mock_stats, \
             patch('endpoint.routes.static_files.generate_stats_image') as mock_gen:
            
            # Setup mocks
            mock_user = MagicMock()
            mock_user.id = 1
            mock_query = MagicMock()
            mock_query.filter_by.return_value.first.return_value = mock_user
            mock_session.return_value.query.return_value = mock_query
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_session.return_value)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            
            mock_stats.return_value = {"total_points": 100}
            mock_gen.return_value = b"fake png image data"
            
            client = app_with_routes.test_client()
            response = client.get('/stats-image/1')
            
            assert response.status_code == 200
            assert response.data == b"fake png image data"
            assert response.content_type == "image/png"
            assert "Cache-Control" in response.headers
            assert "no-cache, no-store" in response.headers["Cache-Control"]
    
    def test_serve_stats_image_user_not_found(self, app_with_routes):
        """Test stats image endpoint when user not found."""
        with patch('endpoint.routes.static_files.is_db_initialized', return_value=True), \
             patch('endpoint.routes.static_files.get_session') as mock_session:
            
            mock_query = MagicMock()
            mock_query.filter_by.return_value.first.return_value = None
            mock_session.return_value.query.return_value = mock_query
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_session.return_value)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            
            client = app_with_routes.test_client()
            response = client.get('/stats-image/999')
            
            assert response.status_code == 404
            data = response.get_json()
            assert "error" in data
            assert "User not found" in data["error"]
    
    def test_serve_stats_image_database_not_available(self, app_with_routes):
        """Test stats image endpoint when database not available."""
        with patch('endpoint.routes.static_files.is_db_initialized', return_value=False):
            client = app_with_routes.test_client()
            response = client.get('/stats-image/1')
            
            assert response.status_code == 503
            data = response.get_json()
            assert "error" in data
            assert "Database not available" in data["error"]
    
    def test_serve_stats_image_no_stats(self, app_with_routes):
        """Test stats image endpoint when stats cannot be generated."""
        with patch('endpoint.routes.static_files.is_db_initialized', return_value=True), \
             patch('endpoint.routes.static_files.get_session') as mock_session, \
             patch('endpoint.routes.static_files.get_user_stats') as mock_stats:
            
            mock_user = MagicMock()
            mock_user.id = 1
            mock_query = MagicMock()
            mock_query.filter_by.return_value.first.return_value = mock_user
            mock_session.return_value.query.return_value = mock_query
            mock_session.return_value.__enter__ = MagicMock(return_value=mock_session.return_value)
            mock_session.return_value.__exit__ = MagicMock(return_value=False)
            
            mock_stats.return_value = None
            
            client = app_with_routes.test_client()
            response = client.get('/stats-image/1')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
            assert "Could not generate stats" in data["error"]
    
    def test_serve_stats_image_exception_handling(self, app_with_routes):
        """Test stats image endpoint handles exceptions."""
        with patch('endpoint.routes.static_files.is_db_initialized', return_value=True), \
             patch('endpoint.routes.static_files.get_session') as mock_session, \
             patch('endpoint.routes.static_files.logger') as mock_logger:
            
            mock_session.side_effect = Exception("Database error")
            
            client = app_with_routes.test_client()
            response = client.get('/stats-image/1')
            
            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
            assert "Error generating image" in data["error"]
            mock_logger.exception.assert_called_once()
    
    def test_request_id_in_logs(self, app_with_routes, project_root_path):
        """Test that request ID is included in logs."""
        with patch('endpoint.routes.static_files.logger') as mock_logger:
            client = app_with_routes.test_client()
            # Make a request for a non-existent sticker to trigger logging
            response = client.get('/stickers/nonexistent.webp', headers={'X-Request-ID': 'test-log-id'})
            
            assert response.status_code == 404
            # Check that logger was called with request_id in extra
            # The logger should have been called during the request (warning for not found)
            assert mock_logger.warning.called, "Logger should be called when sticker not found"
            # Find calls that have extra with request_id
            all_calls = mock_logger.debug.call_args_list + mock_logger.warning.call_args_list
            calls_with_request_id = [
                call for call in all_calls 
                if call and len(call) > 1 and "extra" in call[1] and call[1]["extra"].get("request_id") == "test-log-id"
            ]
            # At least one log call should have request_id matching the header
            assert len(calls_with_request_id) > 0, f"At least one log call should include request_id 'test-log-id'. Found calls: {all_calls}"
