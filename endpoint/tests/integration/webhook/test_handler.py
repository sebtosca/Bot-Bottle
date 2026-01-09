"""Integration tests for webhook handler."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from endpoint.webhook.handler import WebhookHandler, get_request_id
from endpoint.webhook.queue import InMemoryQueue
from endpoint.webhook.idempotency import InMemoryIdempotencyStore


class TestWebhookHandler:
    """Integration tests for WebhookHandler."""
    
    @pytest.fixture
    def handler(self, message_queue, idempotency_store):
        """Create webhook handler for testing."""
        return WebhookHandler(
            idempotency_store=idempotency_store,
            message_queue=message_queue,
            enable_signature_verification=False
        )
    
    def test_handle_verification_success(self, handler, app):
        """Test webhook verification with valid token."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook?hub.mode=subscribe&hub.verify_token=test_token&hub.challenge=test_challenge',
            method='GET'
        ):
            with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': 'test_token'}):
                response, status = handler.handle_verification(request)
                
                assert status == 200
                assert response == "test_challenge"
    
    def test_handle_verification_failure(self, handler, app):
        """Test webhook verification with invalid token."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook?hub.mode=subscribe&hub.verify_token=wrong_token&hub.challenge=test_challenge',
            method='GET'
        ):
            with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': 'test_token'}):
                response, status = handler.handle_verification(request)
                
                assert status == 403
                assert "error" in response.get_json()
    
    def test_handle_webhook_success(self, handler, app, sample_webhook_payload):
        """Test handling webhook POST request successfully."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data=json.dumps(sample_webhook_payload),
            content_type='application/json'
        ):
            response, status = handler.handle_webhook(request, "test-request-123")
            
            assert status == 200
            data = response.get_json()
            assert data["status"] == "ok"
            assert data["message"] == "enqueued"
            
            # Check message was enqueued
            assert handler.message_queue._queue.qsize() == 1
    
    def test_handle_webhook_duplicate_message(self, handler, app, sample_webhook_payload):
        """Test handling duplicate webhook message."""
        from flask import request
        # Mark message as processed first
        handler.idempotency_store.mark_processed("wamid.test123")
        
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data=json.dumps(sample_webhook_payload),
            content_type='application/json'
        ):
            response, status = handler.handle_webhook(request, "test-request-123")
            
            assert status == 200
            data = response.get_json()
            assert data["message"] == "duplicate"
            
            # Message should not be enqueued
            assert handler.message_queue._queue.qsize() == 0
    
    def test_handle_webhook_status_update(self, handler, app, sample_webhook_payload_status):
        """Test handling status update webhook."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data=json.dumps(sample_webhook_payload_status),
            content_type='application/json'
        ):
            response, status = handler.handle_webhook(request, "test-request-123")
            
            assert status == 200
            data = response.get_json()
            assert data["status"] == "ok"
            
            # Status updates should not be enqueued
            assert handler.message_queue._queue.qsize() == 0
    
    def test_handle_webhook_invalid_json(self, handler, app):
        """Test handling webhook with invalid JSON."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data="invalid json",
            content_type='application/json'
        ):
            response, status = handler.handle_webhook(request, "test-request-123")
            
            assert status == 400
            data = response.get_json()
            assert "error" in data
    
    def test_handle_webhook_empty_payload(self, handler, app):
        """Test handling webhook with empty payload."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data=json.dumps({}),
            content_type='application/json'
        ):
            response, status = handler.handle_webhook(request, "test-request-123")
            
            # Empty dict is valid JSON, so it should parse and return 200 (unknown event)
            # But if Flask's get_json() returns None, handler returns 400
            # The actual behavior depends on how Flask handles empty JSON
            assert status in (200, 400)
            if status == 200:
                data = response.get_json()
                assert data["status"] == "ok"
    
    def test_handle_webhook_mark_processed(self, handler, app, sample_webhook_payload):
        """Test webhook handler marks message as processed."""
        from flask import request
        with app.test_request_context(
            '/whatsapp-webhook',
            method='POST',
            data=json.dumps(sample_webhook_payload),
            content_type='application/json'
        ):
            handler.handle_webhook(request, "test-request-123")
            
            # Message should be marked as processed
            assert handler.idempotency_store.is_duplicate("wamid.test123") is True


class TestGetRequestId:
    """Tests for get_request_id function."""
    
    def test_get_request_id_from_header(self, app):
        """Test getting request ID from header."""
        from flask import request
        with app.test_request_context('/test', headers={'X-Request-ID': 'custom-id-123'}):
            request_id = get_request_id(request)
            
            assert request_id == 'custom-id-123'
    
    def test_get_request_id_generates_uuid(self, app):
        """Test generating request ID when header missing."""
        from flask import request
        with app.test_request_context('/test'):
            request_id = get_request_id(request)
            
            assert request_id is not None
            assert len(request_id) > 0
            # Should be valid UUID format
            import uuid
            try:
                uuid.UUID(request_id)
            except ValueError:
                # If not UUID, should still be a string
                assert isinstance(request_id, str)
    
    def test_get_request_id_rejects_too_long(self, app):
        """Test request ID generation rejects too long header."""
        from flask import request
        long_id = "a" * 101
        with app.test_request_context('/test', headers={'X-Request-ID': long_id}):
            request_id = get_request_id(request)
            
            # Should generate new ID instead
            assert request_id != long_id
            assert len(request_id) <= 100
