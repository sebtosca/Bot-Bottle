"""Unit tests for WhatsApp Cloud API client."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from services.whatsapp.client import (
    WhatsAppCloudError,
    _check_api_response,
    _get_headers,
    _get_messages_url,
    send_whatsapp_text,
    send_whatsapp_sticker,
    send_whatsapp_gif,
    send_whatsapp_media,
    send_whatsapp_audio,
    send_whatsapp_interactive_list,
    send_whatsapp_interactive_buttons,
)


@pytest.mark.unit
class TestWhatsAppCloudError:
    """Tests for WhatsAppCloudError exception."""
    
    def test_error_creation(self):
        """Test creating WhatsAppCloudError."""
        error = WhatsAppCloudError("Test error", error_code="10", error_subcode="131030")
        
        assert str(error) == "Test error"
        assert error.error_code == "10"
        assert error.error_subcode == "131030"
        assert error.full_response is None
    
    def test_error_with_full_response(self):
        """Test error with full response."""
        full_response = {"error": {"message": "Test"}}
        error = WhatsAppCloudError("Test", full_response=full_response)
        
        assert error.full_response == full_response


@pytest.mark.unit
class TestCheckApiResponse:
    """Tests for _check_api_response function."""
    
    def test_check_valid_response(self):
        """Test checking valid API response."""
        data = {"messages": [{"id": "test123"}]}
        # Should not raise
        _check_api_response(data, json.dumps(data))
    
    def test_check_error_in_response(self):
        """Test checking response with error field."""
        data = {
            "error": {
                "message": "Test error",
                "code": 10,
                "type": "OAuthException"
            }
        }
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            _check_api_response(data, json.dumps(data))
        
        assert exc_info.value.error_code == 10
        assert "Test error" in str(exc_info.value)
    
    def test_check_errors_array(self):
        """Test checking response with errors array."""
        data = {
            "errors": [{
                "message": "Test error",
                "code": 20
            }]
        }
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            _check_api_response(data, json.dumps(data))
        
        assert exc_info.value.error_code == 20
    
    def test_check_error_in_messages(self):
        """Test checking error embedded in messages."""
        data = {
            "messages": [{
                "id": "test123",
                "errors": [{
                    "message": "Message error",
                    "code": 30
                }]
            }]
        }
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            _check_api_response(data, json.dumps(data))
        
        assert exc_info.value.error_code == 30


@pytest.mark.unit
class TestGetHeaders:
    """Tests for _get_headers function."""
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token_123')
    def test_get_headers_success(self):
        """Test getting headers with valid token."""
        headers = _get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_token_123"
        assert headers["Content-Type"] == "application/json"
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', None)
    def test_get_headers_missing_token(self):
        """Test getting headers without token raises error."""
        with pytest.raises(RuntimeError, match="Missing WHATSAPP_ACCESS_TOKEN"):
            _get_headers()
    
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', '')
    def test_get_headers_empty_token(self):
        """Test getting headers with empty token raises error."""
        with pytest.raises(RuntimeError, match="Missing WHATSAPP_ACCESS_TOKEN"):
            _get_headers()


@pytest.mark.unit
class TestGetMessagesUrl:
    """Tests for _get_messages_url function."""
    
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456789')
    def test_get_messages_url_success(self):
        """Test getting messages URL with valid phone number ID."""
        url = _get_messages_url()
        
        assert "123456789" in url
        assert "/messages" in url
        assert url.startswith("https://graph.facebook.com")
    
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', None)
    def test_get_messages_url_missing_id(self):
        """Test getting URL without phone number ID raises error."""
        with pytest.raises(RuntimeError, match="Missing WHATSAPP_PHONE_NUMBER_ID"):
            _get_messages_url()


@pytest.mark.unit
class TestSendWhatsAppText:
    """Tests for send_whatsapp_text function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_success(self, mock_post, mock_headers, mock_url):
        """Test sending text message successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_text("+33684950535", "Hello!")
        
        assert message_id == "wamid.test123"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://graph.facebook.com/v18.0/123456/messages"
        assert "Authorization" in call_args[1]["headers"]
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_network_error(self, mock_post, mock_headers, mock_url):
        """Test handling network error."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Network error")
        
        with pytest.raises(WhatsAppCloudError, match="Network error"):
            send_whatsapp_text("+33684950535", "Hello!")
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_api_error(self, mock_post, mock_headers, mock_url):
        """Test handling API error response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid phone number",
                "code": 10
            }
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            send_whatsapp_text("+33684950535", "Hello!")
        
        assert exc_info.value.error_code == 10
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_no_messages_in_response(self, mock_post, mock_headers, mock_url):
        """Test handling response without messages field."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No messages field
        mock_response.text = json.dumps({})
        mock_post.return_value = mock_response
        
        with pytest.raises(WhatsAppCloudError, match="No messages field"):
            send_whatsapp_text("+33684950535", "Hello!")
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_invalid_json(self, mock_post, mock_headers, mock_url):
        """Test handling invalid JSON response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON"
        mock_post.return_value = mock_response
        
        with pytest.raises(WhatsAppCloudError, match="Invalid JSON"):
            send_whatsapp_text("+33684950535", "Hello!")
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_phone_normalization(self, mock_post, mock_headers, mock_url):
        """Test phone number normalization logging."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950536"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_text("+33684950535", "Hello!")
        
        assert message_id == "wamid.test123"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_text_invalid_json_with_400_status(self, mock_post, mock_headers, mock_url):
        """Test handling invalid JSON with 400 status code."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON"
        mock_post.return_value = mock_response
        
        with pytest.raises(WhatsAppCloudError, match="WhatsApp Cloud API error 400"):
            send_whatsapp_text("+33684950535", "Hello!")


@pytest.mark.unit
class TestSendWhatsAppSticker:
    """Tests for send_whatsapp_sticker function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_sticker_success(self, mock_post, mock_headers, mock_url):
        """Test sending sticker successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.sticker123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_sticker("+33684950535", "https://example.com/sticker.webp")
        
        assert message_id == "wamid.sticker123"
        # Verify payload structure
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "sticker"
        assert "sticker" in call_data
        assert call_data["sticker"]["link"] == "https://example.com/sticker.webp"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_sticker_phone_normalization(self, mock_post, mock_headers, mock_url):
        """Test phone number normalization in sticker response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.sticker123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950536"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_sticker("+33684950535", "https://example.com/sticker.webp")
        
        assert message_id == "wamid.sticker123"


@pytest.mark.unit
class TestSendWhatsAppGif:
    """Tests for send_whatsapp_gif function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_gif_success(self, mock_post, mock_headers, mock_url):
        """Test sending GIF successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.gif123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_gif("+33684950535", "https://example.com/video.mp4", "Caption")
        
        assert message_id == "wamid.gif123"
        # Verify payload structure
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "video"
        assert "video" in call_data
        assert call_data["video"]["link"] == "https://example.com/video.mp4"
        assert call_data["video"]["caption"] == "Caption"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_gif_without_caption(self, mock_post, mock_headers, mock_url):
        """Test sending GIF without caption."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.gif123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_gif("+33684950535", "https://example.com/video.mp4")
        
        assert message_id == "wamid.gif123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert "caption" not in call_data["video"]
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_gif_phone_normalization(self, mock_post, mock_headers, mock_url):
        """Test phone number normalization in GIF response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.gif123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950536"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_gif("+33684950535", "https://example.com/video.mp4", "Caption")
        
        assert message_id == "wamid.gif123"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_gif_with_status_warning(self, mock_post, mock_headers, mock_url):
        """Test GIF message with status in response triggers warning."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.gif123", "status": "pending"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_gif("+33684950535", "https://example.com/video.mp4")
        
        assert message_id == "wamid.gif123"


@pytest.mark.unit
class TestSendWhatsAppInteractiveList:
    """Tests for send_whatsapp_interactive_list function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_interactive_list_success(self, mock_post, mock_headers, mock_url):
        """Test sending interactive list successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.list123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        options = [
            {"id": "opt1", "title": "Option 1", "description": "First option"},
            {"id": "opt2", "title": "Option 2"}
        ]
        
        message_id = send_whatsapp_interactive_list(
            "+33684950535",
            "Header",
            "Body text",
            "Button",
            options
        )
        
        assert message_id == "wamid.list123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "interactive"
        assert call_data["interactive"]["type"] == "list"
        assert len(call_data["interactive"]["action"]["sections"][0]["rows"]) == 2
    
    def test_send_interactive_list_too_many_options(self):
        """Test sending list with too many options raises error."""
        options = [{"id": f"opt{i}", "title": f"Option {i}"} for i in range(11)]
        
        with pytest.raises(ValueError, match="Maximum 10 options"):
            send_whatsapp_interactive_list(
                "+33684950535",
                "Header",
                "Body",
                "Button",
                options
            )


@pytest.mark.unit
class TestSendWhatsAppInteractiveButtons:
    """Tests for send_whatsapp_interactive_buttons function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_interactive_buttons_success(self, mock_post, mock_headers, mock_url):
        """Test sending interactive buttons successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.button123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        buttons = [
            {"id": "btn1", "title": "Button 1"},
            {"id": "btn2", "title": "Button 2"}
        ]
        
        message_id = send_whatsapp_interactive_buttons(
            "+33684950535",
            "Body text",
            buttons
        )
        
        assert message_id == "wamid.button123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "interactive"
        assert call_data["interactive"]["type"] == "button"
        assert len(call_data["interactive"]["action"]["buttons"]) == 2
    
    def test_send_interactive_buttons_too_many(self):
        """Test sending buttons with too many buttons raises error."""
        buttons = [{"id": f"btn{i}", "title": f"Button {i}"} for i in range(4)]
        
        with pytest.raises(ValueError, match="Maximum 3 buttons"):
            send_whatsapp_interactive_buttons(
                "+33684950535",
                "Body",
                buttons
            )


@pytest.mark.unit
class TestSendWhatsAppMedia:
    """Tests for send_whatsapp_media function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_media_success(self, mock_post, mock_headers, mock_url):
        """Test sending media message successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.media123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_media("+33684950535", "https://example.com/image.jpg", "Caption")
        
        assert message_id == "wamid.media123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "image"
        assert call_data["image"]["link"] == "https://example.com/image.jpg"
        assert call_data["image"]["caption"] == "Caption"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_media_without_caption(self, mock_post, mock_headers, mock_url):
        """Test sending media without caption."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.media123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_media("+33684950535", "https://example.com/image.jpg")
        
        assert message_id == "wamid.media123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert "caption" not in call_data["image"]
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_media_phone_normalization(self, mock_post, mock_headers, mock_url):
        """Test phone number normalization logging in media response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.media123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950536"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_media("+33684950535", "https://example.com/image.jpg")
        
        assert message_id == "wamid.media123"


@pytest.mark.unit
class TestSendWhatsAppAudio:
    """Tests for send_whatsapp_audio function."""
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_audio_success(self, mock_post, mock_headers, mock_url):
        """Test sending audio message successfully."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.audio123"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_audio("+33684950535", "https://example.com/audio.mp3")
        
        assert message_id == "wamid.audio123"
        call_data = json.loads(mock_post.call_args[1]["data"])
        assert call_data["type"] == "audio"
        assert call_data["audio"]["link"] == "https://example.com/audio.mp3"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_audio_with_status_warning(self, mock_post, mock_headers, mock_url):
        """Test audio message with status in response triggers warning."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.audio123", "status": "pending"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_audio("+33684950535", "https://example.com/audio.mp3")
        
        assert message_id == "wamid.audio123"
    
    @patch('services.whatsapp.client._get_messages_url')
    @patch('services.whatsapp.client._get_headers')
    @patch('services.whatsapp.client.requests.post')
    @patch('services.whatsapp.client.WHATSAPP_ACCESS_TOKEN', 'test_token')
    @patch('services.whatsapp.client.WHATSAPP_PHONE_NUMBER_ID', '123456')
    def test_send_audio_phone_normalization(self, mock_post, mock_headers, mock_url):
        """Test phone number normalization logging in audio response."""
        mock_url.return_value = "https://graph.facebook.com/v18.0/123456/messages"
        mock_headers.return_value = {"Authorization": "Bearer test_token"}
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.audio123"}],
            "contacts": [{"wa_id": "+33684950535", "input": "+33684950536"}]
        }
        mock_response.text = json.dumps(mock_response.json.return_value)
        mock_post.return_value = mock_response
        
        message_id = send_whatsapp_audio("+33684950535", "https://example.com/audio.mp3")
        
        assert message_id == "wamid.audio123"


@pytest.mark.unit
class TestCheckApiResponseEdgeCases:
    """Tests for edge cases in _check_api_response."""
    
    def test_check_empty_errors_array(self):
        """Test checking response with empty errors array."""
        data = {"errors": []}
        # Should not raise
        _check_api_response(data, json.dumps(data))
    
    def test_check_errors_array_not_list(self):
        """Test checking response with errors not a list."""
        data = {"errors": "not a list"}
        # Should not raise (only checks if it's a list)
        _check_api_response(data, json.dumps(data))
    
    def test_check_messages_with_non_list_errors(self):
        """Test checking messages with non-list errors."""
        data = {
            "messages": [{
                "id": "test123",
                "errors": {"message": "Error", "code": 10}
            }]
        }
        
        with pytest.raises(WhatsAppCloudError) as exc_info:
            _check_api_response(data, json.dumps(data))
        
        assert exc_info.value.error_code == 10
