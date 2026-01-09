"""Unit tests for webhook validator module."""

import pytest
import hmac
import hashlib
from unittest.mock import Mock, patch
from endpoint.webhook.validator import verify_webhook_signature, verify_webhook_token


class TestVerifyWebhookSignature:
    """Tests for verify_webhook_signature function."""
    
    def test_verify_valid_signature(self):
        """Test verifying valid webhook signature."""
        app_secret = "test_secret_key"
        payload = b'{"test": "data"}'
        
        # Compute expected signature
        expected_sig = hmac.new(
            app_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Create mock request
        request = Mock()
        request.headers.get.return_value = f"sha256={expected_sig}"
        request.get_data.return_value = payload
        
        with patch.dict('os.environ', {'WHATSAPP_APP_SECRET': app_secret}):
            result = verify_webhook_signature(request)
        
        assert result is True
    
    def test_verify_invalid_signature(self):
        """Test verifying invalid webhook signature."""
        app_secret = "test_secret_key"
        payload = b'{"test": "data"}'
        
        # Create mock request with wrong signature
        request = Mock()
        request.headers.get.return_value = "sha256=invalid_signature"
        request.get_data.return_value = payload
        
        with patch.dict('os.environ', {'WHATSAPP_APP_SECRET': app_secret}):
            result = verify_webhook_signature(request)
        
        assert result is False
    
    def test_verify_no_app_secret(self):
        """Test signature verification when app secret is not set."""
        request = Mock()
        
        with patch.dict('os.environ', {}, clear=True):
            result = verify_webhook_signature(request)
        
        assert result is True  # Verification disabled
    
    def test_verify_no_signature_header(self):
        """Test signature verification when header is missing."""
        app_secret = "test_secret_key"
        
        request = Mock()
        request.headers.get.return_value = None
        
        with patch.dict('os.environ', {'WHATSAPP_APP_SECRET': app_secret}):
            result = verify_webhook_signature(request)
        
        assert result is False
    
    def test_verify_invalid_signature_format(self):
        """Test signature verification with invalid format."""
        app_secret = "test_secret_key"
        
        request = Mock()
        request.headers.get.return_value = "invalid_format"
        request.get_data.return_value = b'{"test": "data"}'
        
        with patch.dict('os.environ', {'WHATSAPP_APP_SECRET': app_secret}):
            result = verify_webhook_signature(request)
        
        assert result is False
    
    def test_verify_empty_body(self):
        """Test signature verification with empty body."""
        app_secret = "test_secret_key"
        
        request = Mock()
        request.headers.get.return_value = "sha256=test"
        request.get_data.return_value = b''
        
        with patch.dict('os.environ', {'WHATSAPP_APP_SECRET': app_secret}):
            result = verify_webhook_signature(request)
        
        assert result is False


class TestVerifyWebhookToken:
    """Tests for verify_webhook_token function."""
    
    def test_verify_valid_token(self):
        """Test verifying valid webhook token."""
        expected_token = "test_verify_token"
        
        with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': expected_token}):
            result = verify_webhook_token("subscribe", expected_token)
        
        assert result is True
    
    def test_verify_invalid_token(self):
        """Test verifying invalid webhook token."""
        expected_token = "test_verify_token"
        
        with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': expected_token}):
            result = verify_webhook_token("subscribe", "wrong_token")
        
        assert result is False
    
    def test_verify_wrong_mode(self):
        """Test verifying token with wrong mode."""
        expected_token = "test_verify_token"
        
        with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': expected_token}):
            result = verify_webhook_token("unsubscribe", expected_token)
        
        assert result is False
    
    def test_verify_no_token_env(self):
        """Test verifying token when env var is not set."""
        with patch.dict('os.environ', {}, clear=True):
            result = verify_webhook_token("subscribe", "any_token")
        
        assert result is False
    
    def test_verify_none_token(self):
        """Test verifying with None token."""
        expected_token = "test_verify_token"
        
        with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': expected_token}):
            result = verify_webhook_token("subscribe", None)
        
        assert result is False
    
    def test_verify_none_mode(self):
        """Test verifying with None mode."""
        expected_token = "test_verify_token"
        
        with patch.dict('os.environ', {'WHATSAPP_VERIFY_TOKEN': expected_token}):
            result = verify_webhook_token(None, expected_token)
        
        assert result is False
