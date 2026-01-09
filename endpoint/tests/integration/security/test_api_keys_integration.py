"""Integration tests for API key handling and validation."""

import pytest
import os
from unittest.mock import patch
from endpoint.security.api_keys import (
    get_key,
    mask_key,
    validate_api_keys,
    KEYS,
)


class TestApiKeysIntegration:
    """Integration tests for API key functions with real environment."""
    
    def test_get_key_integration_required(self):
        """Test get_key with real environment variable (required)."""
        test_key = "TEST_INTEGRATION_KEY_REQUIRED"
        test_value = "integration_test_value_12345"
        
        # Clean up before and after
        original_value = os.environ.get(test_key)
        try:
            os.environ[test_key] = test_value
            result = get_key(test_key, required=True)
            assert result == test_value
        finally:
            if original_value is not None:
                os.environ[test_key] = original_value
            elif test_key in os.environ:
                del os.environ[test_key]
    
    def test_get_key_integration_optional(self):
        """Test get_key with real environment variable (optional)."""
        test_key = "TEST_INTEGRATION_KEY_OPTIONAL"
        
        # Clean up before and after
        original_value = os.environ.get(test_key)
        try:
            # Test when not set
            if test_key in os.environ:
                del os.environ[test_key]
            result = get_key(test_key, required=False)
            assert result is None
            
            # Test when set
            os.environ[test_key] = "optional_value"
            result = get_key(test_key, required=False)
            assert result == "optional_value"
        finally:
            if original_value is not None:
                os.environ[test_key] = original_value
            elif test_key in os.environ:
                del os.environ[test_key]
    
    def test_validate_api_keys_integration_all_set(self):
        """Test validate_api_keys with all required keys set in environment."""
        # Save original environment
        original_env = {}
        test_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        
        for key in test_keys:
            original_env[key] = os.environ.get(key)
        
        try:
            # Set all required keys
            for key in test_keys:
                os.environ[key] = f"test_{key.lower()}_value"
            
            # Should not raise
            result = validate_api_keys()
            assert isinstance(result, dict)
            assert len(result) == len(KEYS)
            
            # All required keys should be marked as set
            for key in test_keys:
                assert result[key]["set"] is True
                assert result[key]["required"] is True
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
    
    def test_validate_api_keys_integration_missing_required(self):
        """Test validate_api_keys raises when required keys missing."""
        # Save original environment
        original_env = {}
        test_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        
        for key in test_keys:
            original_env[key] = os.environ.get(key)
            # Remove keys for test
            if key in os.environ:
                del os.environ[key]
        
        try:
            # Should raise RuntimeError
            with pytest.raises(RuntimeError) as exc_info:
                validate_api_keys()
            
            assert "Missing required API keys" in str(exc_info.value)
            # Should mention at least one missing key
            error_msg = str(exc_info.value)
            assert any(key in error_msg for key in test_keys)
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
    
    def test_validate_api_keys_integration_partial_set(self):
        """Test validate_api_keys with some required keys missing."""
        # Save original environment
        original_env = {}
        test_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        
        for key in test_keys:
            original_env[key] = os.environ.get(key)
        
        try:
            # Set only some required keys
            os.environ["WHATSAPP_ACCESS_TOKEN"] = "test_token"
            os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test_phone"
            # Missing WHATSAPP_VERIFY_TOKEN and MISTRAL_API_KEY
            
            with pytest.raises(RuntimeError) as exc_info:
                validate_api_keys()
            
            error_msg = str(exc_info.value)
            assert "Missing required API keys" in error_msg
            # Should mention missing keys
            assert "WHATSAPP_VERIFY_TOKEN" in error_msg or "MISTRAL_API_KEY" in error_msg
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
    
    def test_validate_api_keys_integration_with_optional(self):
        """Test validate_api_keys with optional keys set."""
        # Save original environment
        original_env = {}
        required_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        optional_keys = [
            "WHATSAPP_APP_SECRET",
            "WHATSAPP_ACCOUNT_ID",
        ]
        
        all_keys = required_keys + optional_keys
        for key in all_keys:
            original_env[key] = os.environ.get(key)
        
        try:
            # Set all required and optional keys
            for key in all_keys:
                os.environ[key] = f"test_{key.lower()}_value"
            
            result = validate_api_keys()
            
            # All keys should be in result
            for key in all_keys:
                assert key in result
                assert result[key]["set"] is True
            
            # Optional keys should be marked as not required
            for key in optional_keys:
                assert result[key]["required"] is False
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
    
    def test_mask_key_integration_real_values(self):
        """Test mask_key with realistic API key values."""
        test_cases = [
            ("sk-1234567890abcdef", "sk-1...cdef"),  # Typical API key format
            ("EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", "EAAx...xxxx"),  # Long token
            ("short", "***"),  # Short key
            ("", "***"),  # Empty
            (None, "***"),  # None
        ]
        
        for value, expected in test_cases:
            result = mask_key(value)
            assert result == expected, f"mask_key({value!r}) should return {expected!r}, got {result!r}"
    
    def test_get_key_error_message_format(self):
        """Test get_key error message format is helpful."""
        test_key = "TEST_ERROR_FORMAT_KEY"
        original_value = os.environ.get(test_key)
        
        try:
            if test_key in os.environ:
                del os.environ[test_key]
            
            with pytest.raises(RuntimeError) as exc_info:
                get_key(test_key, required=True, description="This is a test key for integration testing")
            
            error_msg = str(exc_info.value)
            assert test_key in error_msg
            assert "required" in error_msg.lower()
            assert "env" in error_msg.lower() or ".env" in error_msg.lower()
            assert "This is a test key" in error_msg
        finally:
            if original_value is not None:
                os.environ[test_key] = original_value
            elif test_key in os.environ:
                del os.environ[test_key]
    
    def test_validate_api_keys_status_structure(self):
        """Test validate_api_keys returns properly structured status."""
        # Save original environment
        original_env = {}
        test_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        
        for key in test_keys:
            original_env[key] = os.environ.get(key)
            os.environ[key] = f"test_{key.lower()}_value"
        
        try:
            result = validate_api_keys()
            
            # Check structure
            assert isinstance(result, dict)
            for key_name, status in result.items():
                assert isinstance(status, dict)
                assert "set" in status
                assert "required" in status
                assert isinstance(status["set"], bool)
                assert isinstance(status["required"], bool)
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
    
    def test_validate_api_keys_empty_string_handling(self):
        """Test validate_api_keys treats empty strings as missing."""
        # Save original environment
        original_env = {}
        test_keys = [
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        ]
        
        for key in test_keys:
            original_env[key] = os.environ.get(key)
        
        try:
            # Set one key to empty string
            os.environ["WHATSAPP_ACCESS_TOKEN"] = ""
            os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "test_phone"
            os.environ["WHATSAPP_VERIFY_TOKEN"] = "test_verify"
            os.environ["MISTRAL_API_KEY"] = "test_mistral"
            
            with pytest.raises(RuntimeError) as exc_info:
                validate_api_keys()
            
            assert "Missing required API keys" in str(exc_info.value)
            assert "WHATSAPP_ACCESS_TOKEN" in str(exc_info.value)
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is not None:
                    os.environ[key] = value
                elif key in os.environ:
                    del os.environ[key]
