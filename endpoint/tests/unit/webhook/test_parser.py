"""Unit tests for webhook parser module."""

import pytest
from endpoint.webhook.parser import parse_webhook_payload, parse_message
from endpoint.webhook.parser import extract_stable_id
from endpoint.webhook.models import WebhookEvent, ParsedMessage


class TestParseWebhookPayload:
    """Tests for parse_webhook_payload function."""
    
    def test_parse_production_webhook_format(self, sample_webhook_payload):
        """Test parsing production webhook format."""
        event = parse_webhook_payload(sample_webhook_payload)
        
        assert event.event_type == "message"
        assert event.message is not None
        assert event.message_id == "wamid.test123"
        assert event.error is None
    
    def test_parse_test_webhook_format(self, sample_webhook_payload_test_format):
        """Test parsing test webhook format (direct value)."""
        event = parse_webhook_payload(sample_webhook_payload_test_format)
        
        assert event.event_type == "message"
        assert event.message is not None
        assert event.message_id == "wamid.test123"
    
    def test_parse_status_update(self, sample_webhook_payload_status):
        """Test parsing status update webhook."""
        event = parse_webhook_payload(sample_webhook_payload_status)
        
        assert event.event_type == "status"
        assert event.message is None
        assert event.message_id == "wamid.test123"
    
    def test_parse_empty_payload(self):
        """Test parsing empty payload."""
        event = parse_webhook_payload({})
        
        assert event.event_type == "unknown"
        assert event.message is None
        assert event.error is not None
    
    def test_parse_invalid_payload_type(self):
        """Test parsing invalid payload type."""
        event = parse_webhook_payload("not a dict")
        
        assert event.event_type == "unknown"
        assert event.error == "Invalid payload: not a dict"
    
    def test_parse_webhook_with_no_messages(self):
        """Test parsing webhook with no messages."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {}
                }]
            }]
        }
        event = parse_webhook_payload(payload)
        
        assert event.event_type == "unknown"
        assert event.message is None
    
    def test_parse_webhook_with_invalid_message_format(self):
        """Test parsing webhook with invalid message format."""
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": ["not a dict"]
                    }
                }]
            }]
        }
        event = parse_webhook_payload(payload)
        
        assert event.event_type == "unknown"
        assert "Invalid message format" in event.error or event.message is None


class TestParseMessage:
    """Tests for parse_message function."""
    
    def test_parse_text_message(self):
        """Test parsing text message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"},
            "context": {"product": "00001"}
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_id == "wamid.test123"
        assert parsed.from_number == "15551234567"
        assert parsed.message_type == "text"
        assert parsed.body == "Hello!"
        assert parsed.product_id == "00001"
        assert parsed.num_media == 0
    
    def test_parse_image_message(self):
        """Test parsing image message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "image",
            "image": {"mime_type": "image/jpeg"},
            "context": {"product": "00001"}
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_type == "image"
        assert parsed.num_media == 1
        assert parsed.media_type == "image/jpeg"
    
    def test_parse_sticker_message(self):
        """Test parsing sticker message."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "sticker",
            "sticker": {},
            "context": {"product": "00001"}
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_type == "sticker"
        assert parsed.num_media == 1
        assert parsed.media_type == "image/webp"
    
    def test_parse_interactive_list_message(self):
        """Test parsing interactive list selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "00002"}
            }
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_type == "interactive"
        assert parsed.body == "[SWITCH_CHARACTER:00002]"
    
    def test_parse_interactive_button_message(self):
        """Test parsing interactive button selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "00002"}
            }
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_type == "interactive"
        assert parsed.body == "[SWITCH_CHARACTER:00002]"
    
    def test_parse_interactive_stats_button(self):
        """Test parsing stats button selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "stats_points"}
            }
        }
        
        parsed = parse_message(message)
        
        assert parsed.body == "[STATS_BUTTON:stats_points]"
    
    def test_parse_interactive_feed_button(self):
        """Test parsing feed button selection."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "FEED_00001"}
            }
        }
        
        parsed = parse_message(message)
        
        assert parsed.body == "[FEED_CHARACTER:00001]"
    
    def test_parse_message_missing_id(self):
        """Test parsing message with missing ID."""
        message = {
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"}
        }
        
        with pytest.raises(ValueError, match="Missing required field: id"):
            parse_message(message)
    
    def test_parse_message_missing_from(self):
        """Test parsing message with missing from number."""
        message = {
            "id": "wamid.test123",
            "type": "text",
            "text": {"body": "Hello!"}
        }
        
        with pytest.raises(ValueError, match="Missing required field: from"):
            parse_message(message)
    
    def test_parse_message_invalid_type(self):
        """Test parsing message with invalid type."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "invalid_type"
        }
        
        parsed = parse_message(message)
        
        assert parsed.message_type == "invalid_type"
        assert parsed.body == ""
    
    def test_parse_message_default_product_id(self):
        """Test parsing message defaults to Cherry product ID."""
        message = {
            "id": "wamid.test123",
            "from": "15551234567",
            "type": "text",
            "text": {"body": "Hello!"}
        }
        
        parsed = parse_message(message)
        
        assert parsed.product_id == "00001"  # Default to Cherry


class TestExtractStableId:
    """Tests for extract_stable_id function."""
    
    def test_extract_stable_id_from_message_event(self):
        """Test extracting stable ID from message event."""
        event = WebhookEvent(
            event_type="message",
            message={"id": "wamid.test123"},
            message_id="wamid.test123"
        )
        
        stable_id = extract_stable_id(event)
        
        assert stable_id == "wamid.test123"
    
    def test_extract_stable_id_from_status_event(self):
        """Test extracting stable ID from status event."""
        event = WebhookEvent(
            event_type="status",
            message_id="wamid.test123"
        )
        
        stable_id = extract_stable_id(event)
        
        assert stable_id == "wamid.test123"
    
    def test_extract_stable_id_no_message_id(self):
        """Test extracting stable ID when message_id is missing."""
        event = WebhookEvent(
            event_type="message",
            message={"id": "wamid.test123"},
            message_id=None
        )
        
        stable_id = extract_stable_id(event)
        
        assert stable_id == "wamid.test123"
    
    def test_extract_stable_id_unknown_event(self):
        """Test extracting stable ID from unknown event."""
        event = WebhookEvent(
            event_type="unknown",
            message_id=None
        )
        
        stable_id = extract_stable_id(event)
        
        assert stable_id is None
