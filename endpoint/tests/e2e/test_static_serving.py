"""End-to-end tests for static file serving."""

import pytest
from pathlib import Path
from endpoint.endpoint import app


@pytest.mark.e2e
class TestStaticServing:
    """End-to-end tests for static file serving."""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client."""
        app.config['TESTING'] = True
        return app.test_client()
    
    def test_health_check_e2e(self, client):
        """Test health check endpoint end-to-end."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
    
    def test_sticker_serving_e2e(self, client, project_root_path):
        """Test serving sticker file end-to-end."""
        # Check if stickers directory exists
        stickers_dir = project_root_path / "stickers"
        if not stickers_dir.exists():
            pytest.skip("Stickers directory not found")
        
        # Find a real sticker file
        sticker_files = list(stickers_dir.glob("*.webp"))
        if not sticker_files:
            pytest.skip("No sticker files found")
        
        test_sticker = sticker_files[0].name
        
        # Request the sticker
        response = client.get(f'/stickers/{test_sticker}')
        
        assert response.status_code == 200
        assert len(response.data) > 0
        assert response.content_type.startswith("image/")
