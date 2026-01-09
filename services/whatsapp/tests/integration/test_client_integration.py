"""Integration tests for WhatsApp client."""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from services.whatsapp.client import (
    send_whatsapp_text,
    send_whatsapp_sticker,
    send_whatsapp_gif,
    WhatsAppCloudError,
)


@pytest.mark.integration
class TestWhatsAppClientIntegration:
    """Integration tests for WhatsApp client with mocked HTTP."""
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    @patch('services.whatsapp.client.requests.post')
    def test_send_text_full_flow(self, mock_post):
        """Test complete text message sending flow."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950535"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_text("+33684950535", "Hello, integration test!")
        
        assert message_id == "wamid.test123"
        assert mock_post.called
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "text"
        assert call_data["text"]["body"] == "Hello, integration test!"
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    @patch('services.whatsapp.client.requests.post')
    def test_send_sticker_full_flow(self, mock_post):
        """Test complete sticker sending flow."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.sticker123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_sticker("+33684950535", "https://example.com/sticker.webp")
        
        assert message_id == "wamid.sticker123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "sticker"
        assert call_data["sticker"]["link"] == "https://example.com/sticker.webp"
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    @patch('services.whatsapp.client.requests.post')
    def test_send_gif_with_caption(self, mock_post):
        """Test sending GIF with caption."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.gif123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_gif("+33684950535", "https://example.com/video.mp4", "Fun GIF!")
        
        assert message_id == "wamid.gif123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "video"
        assert call_data["video"]["caption"] == "Fun GIF!"
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    @patch('services.whatsapp.client.requests.post')
    def test_error_propagation(self, mock_post):
        """Test error propagation through full flow."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid phone number",
                "code": 10,
                "type": "OAuthException"
            }
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            send_whatsapp_text("+33684950535", "Hello")
        
        assert exc_info.value.error_code == 10
        assert "Invalid phone number" in str(exc_info.value)
