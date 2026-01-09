"""Unit tests for webhook models."""

import pytest
from endpoint.webhook.models import WebhookEvent, ParsedMessage, JobPayload


class TestWebhookEvent:
    """Tests for WebhookEvent model."""
    
    def test_message_event_properties(self):
        """Test WebhookEvent properties for message events."""
        event = WebhookEvent(
            event_type="message",
            message={"id": "wamid.test123"},
            message_id="wamid.test123"
        )
        
        assert event.is_message is True
        assert event.is_duplicate is False
    
    def test_status_event_properties(self):
        """Test WebhookEvent properties for status events."""
        event = WebhookEvent(
            event_type="status",
            message_id="wamid.test123"
        )
        
        assert event.is_message is False
        assert event.is_duplicate is False
    
    def test_duplicate_event_properties(self):
        """Test WebhookEvent properties for duplicate events."""
        event = WebhookEvent(
            event_type="message",
            message={"id": "wamid.test123"},
            message_id="wamid.test123",
            error="duplicate"
        )
        
        assert event.is_duplicate is True
    
    def test_message_event_without_message(self):
        """Test WebhookEvent with message type but no message dict."""
        event = WebhookEvent(
            event_type="message",
            message=None
        )
        
        assert event.is_message is False


class TestParsedMessage:
    """Tests for ParsedMessage model."""
    
    def test_from_webhook_message_text(self):
        """Test creating ParsedMessage from text webhook message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"},
            "context": {"product": "00001"}
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.message_id == "wamid.test123"
        assert parsed.from_number == "15551234567"
        assert parsed.message_type == "text"
        assert parsed.body == "Hello!"
        assert parsed.product_id == "00001"
        assert parsed.num_media == 0
        assert parsed.media_type == ""
    
    def test_from_webhook_message_image(self):
        """Test creating ParsedMessage from image webhook message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "image",
            "image": {"mime_type": "image/jpeg"}
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.message_type == "image"
        assert parsed.num_media == 1
        assert parsed.media_type == "image/jpeg"
    
    def test_from_webhook_message_default_product_id(self):
        """Test ParsedMessage defaults to Cherry product ID."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"}
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.product_id == "00001"
    
    def test_from_webhook_message_product_id_from_context(self):
        """Test ParsedMessage extracts product_id from context."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"},
            "context": {"product": "00002"}
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.product_id == "00002"
    
    def test_from_webhook_message_interactive_list(self):
        """Test ParsedMessage from interactive list selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "00002"}
            }
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.body == "[SWITCH_CHARACTER:00002]"
    
    def test_from_webhook_message_interactive_button(self):
        """Test ParsedMessage from interactive button selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "00002"}
            }
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.body == "[SWITCH_CHARACTER:00002]"
    
    def test_from_webhook_message_sticker(self):
        """Test ParsedMessage from sticker message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "sticker",
            "sticker": {}
        }
        
        parsed = ParsedMessage.from_webhook_message(message)
        
        assert parsed.message_type == "sticker"
        assert parsed.num_media == 1
        assert parsed.media_type == "image/webp"


class TestJobPayload:
    """Tests for JobPayload model."""
    
    def test_job_payload_creation(self, sample_parsed_message):
        """Test creating JobPayload from ParsedMessage."""
        import time
        
        payload = JobPayload(
            request_id="test-request-123",
            message_id=sample_parsed_message.message_id,
            from_number=sample_parsed_message.from_number,
            message_type=sample_parsed_message.message_type,
            body=sample_parsed_message.body,
            num_media=sample_parsed_message.num_media,
            media_type=sample_parsed_message.media_type,
            product_id=sample_parsed_message.product_id,
            raw_message=sample_parsed_message.raw_message,
            timestamp=time.time()
        )
        
        assert payload.request_id == "test-request-123"
        assert payload.message_id == sample_parsed_message.message_id
        assert payload.from_number == sample_parsed_message.from_number
        assert payload.timestamp > 0
