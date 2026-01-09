"""Unit tests for API key handling and validation."""

import pytest
import os
from unittest.mock import patch, MagicMock
from endpoint.security.api_keys import (
    get_key,
    mask_key,
    validate_api_keys,
    KeySpec,
    KEYS,
)


class TestKeySpec:
    """Tests for KeySpec dataclass."""
    
    def test_keyspec_creation(self):
        """Test KeySpec can be created with all parameters."""
        spec = KeySpec("TEST_KEY", required=True, description="Test key")
        assert spec.name == "TEST_KEY"
        assert spec.required is True
        assert spec.description == "Test key"
    
    def test_keyspec_defaults(self):
        """Test KeySpec defaults."""
        spec = KeySpec("TEST_KEY")
        assert spec.name == "TEST_KEY"
        assert spec.required is True  # Default
        assert spec.description == ""  # Default
    
    def test_keyspec_frozen(self):
        """Test KeySpec is frozen (immutable)."""
        spec = KeySpec("TEST_KEY", required=False)
        with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
            spec.name = "NEW_NAME"
    
    def test_keys_specs_defined(self):
        """Test that KEYS tuple contains expected key specs."""
        key_names = {spec.name for spec in KEYS}
        expected_keys = {
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
            "WHATSAPP_APP_SECRET",
            "WHATSAPP_ACCOUNT_ID",
        }
        assert key_names == expected_keys
    
    def test_required_keys_identified(self):
        """Test that required keys are properly marked."""
        required_keys = {spec.name for spec in KEYS if spec.required}
        expected_required = {
            "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_VERIFY_TOKEN",
            "MISTRAL_API_KEY",
        }
        assert required_keys == expected_required
    
    def test_optional_keys_identified(self):
        """Test that optional keys are properly marked."""
        optional_keys = {spec.name for spec in KEYS if not spec.required}
        expected_optional = {
            "WHATSAPP_APP_SECRET",
            "WHATSAPP_ACCOUNT_ID",
        }
        assert optional_keys == expected_optional


class TestGetKey:
    """Tests for get_key function."""
    
    def test_get_key_returns_value_when_set(self):
        """Test get_key returns value when environment variable is set."""
        with patch.dict(os.environ, {"TEST_KEY": "test_value"}):
            result = get_key("TEST_KEY")
            assert result == "test_value"
    
    def test_get_key_returns_none_when_not_set_optional(self):
        """Test get_key returns None when key not set and required=False."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_key("TEST_KEY", required=False)
            assert result is None
    
    def test_get_key_raises_when_required_missing(self):
        """Test get_key raises RuntimeError when required key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                get_key("TEST_KEY", required=True)
            assert "TEST_KEY is required" in str(exc_info.value)
    
    def test_get_key_raises_with_description(self):
        """Test get_key includes description in error message."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                get_key("TEST_KEY", required=True, description="Test description")
            assert "TEST_KEY is required" in str(exc_info.value)
            assert "Test description" in str(exc_info.value)
    
    def test_get_key_handles_empty_string_as_missing(self):
        """Test get_key treats empty string as missing."""
        with patch.dict(os.environ, {"TEST_KEY": ""}):
            with pytest.raises(RuntimeError) as exc_info:
                get_key("TEST_KEY", required=True)
            assert "TEST_KEY is required" in str(exc_info.value)
    
    def test_get_key_returns_none_for_empty_string_optional(self):
        """Test get_key returns None for empty string when optional."""
        with patch.dict(os.environ, {"TEST_KEY": ""}):
            result = get_key("TEST_KEY", required=False)
            assert result is None
    
    def test_get_key_never_logs_value(self):
        """Test get_key never logs the actual key value."""
        with patch.dict(os.environ, {"TEST_KEY": "secret_value"}), \
             patch('endpoint.security.api_keys.logger') as mock_logger:
            result = get_key("TEST_KEY")
            assert result == "secret_value"
            # Verify no log calls contain the secret value
            for call in mock_logger.info.call_args_list + mock_logger.warning.call_args_list + mock_logger.error.call_args_list:
                if call:
                    call_str = str(call)
                    assert "secret_value" not in call_str


class TestMaskKey:
    """Tests for mask_key function."""
    
    def test_mask_key_short_value(self):
        """Test mask_key masks short values."""
        assert mask_key("short") == "***"
        assert mask_key("1234567") == "***"  # 7 chars, <= 8
        assert mask_key("12345678") == "***"  # 8 chars, <= 8
    
    def test_mask_key_long_value(self):
        """Test mask_key masks long values showing first and last 4 chars."""
        assert mask_key("1234567890") == "1234...7890"
        assert mask_key("abcdefghijklmnop") == "abcd...mnop"
    
    def test_mask_key_none(self):
        """Test mask_key handles None."""
        assert mask_key(None) == "***"
    
    def test_mask_key_empty_string(self):
        """Test mask_key handles empty string."""
        assert mask_key("") == "***"
    
    def test_mask_key_exactly_9_chars(self):
        """Test mask_key with exactly 9 characters."""
        result = mask_key("123456789")
        assert result == "1234...6789"
        assert len(result) > len("123456789")  # Masked version is longer
    
    def test_mask_key_very_long_value(self):
        """Test mask_key with very long value."""
        long_key = "a" * 100
        result = mask_key(long_key)
        assert result.startswith("aaaa")
        assert result.endswith("aaaa")
        assert "..." in result


class TestValidateApiKeys:
    """Tests for validate_api_keys function."""
    
    def test_validate_api_keys_all_required_set(self):
        """Test validate_api_keys succeeds when all required keys are set."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
        }
        with patch.dict(os.environ, env_vars, clear=True), \
             patch('endpoint.security.api_keys.logger') as mock_logger:
            result = validate_api_keys()
            
            assert isinstance(result, dict)
            # Check all required keys are marked as set
            for key_name in ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", 
                           "WHATSAPP_VERIFY_TOKEN", "MISTRAL_API_KEY"]:
                assert key_name in result
                assert result[key_name]["set"] is True
                assert result[key_name]["required"] is True
            
            # Should log success
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "API key validation ok" in call_args[0][0]
    
    def test_validate_api_keys_with_optional_keys(self):
        """Test validate_api_keys handles optional keys."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
            "WHATSAPP_APP_SECRET": "secret123",  # Optional
            "WHATSAPP_ACCOUNT_ID": "account123",  # Optional
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = validate_api_keys()
            
            # Check optional keys
            assert result["WHATSAPP_APP_SECRET"]["set"] is True
            assert result["WHATSAPP_APP_SECRET"]["required"] is False
            assert result["WHATSAPP_ACCOUNT_ID"]["set"] is True
            assert result["WHATSAPP_ACCOUNT_ID"]["required"] is False
    
    def test_validate_api_keys_missing_required(self):
        """Test validate_api_keys raises when required keys are missing."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            # Missing other required keys
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                validate_api_keys()
            assert "Missing required API keys" in str(exc_info.value)
            # Should list missing keys
            assert "WHATSAPP_PHONE_NUMBER_ID" in str(exc_info.value) or \
                   "WHATSAPP_VERIFY_TOKEN" in str(exc_info.value) or \
                   "MISTRAL_API_KEY" in str(exc_info.value)
    
    def test_validate_api_keys_empty_string_treated_as_missing(self):
        """Test validate_api_keys treats empty string as missing."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                validate_api_keys()
            assert "Missing required API keys" in str(exc_info.value)
            assert "WHATSAPP_ACCESS_TOKEN" in str(exc_info.value)
    
    def test_validate_api_keys_optional_missing_ok(self):
        """Test validate_api_keys succeeds when optional keys are missing."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
            # Optional keys not set
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = validate_api_keys()
            
            # Optional keys should be marked as not set but not cause error
            assert result["WHATSAPP_APP_SECRET"]["set"] is False
            assert result["WHATSAPP_APP_SECRET"]["required"] is False
            assert result["WHATSAPP_ACCOUNT_ID"]["set"] is False
            assert result["WHATSAPP_ACCOUNT_ID"]["required"] is False
    
    def test_validate_api_keys_returns_status_for_all_keys(self):
        """Test validate_api_keys returns status for all keys in KEYS."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            result = validate_api_keys()
            
            # Should have status for all keys
            assert len(result) == len(KEYS)
            for spec in KEYS:
                assert spec.name in result
                assert "set" in result[spec.name]
                assert "required" in result[spec.name]
                assert isinstance(result[spec.name]["set"], bool)
                assert isinstance(result[spec.name]["required"], bool)
    
    def test_validate_api_keys_logs_missing_count(self):
        """Test validate_api_keys logs missing required count."""
        env_vars = {
            "WHATSAPP_ACCESS_TOKEN": "token123",
            "WHATSAPP_PHONE_NUMBER_ID": "phone123",
            "WHATSAPP_VERIFY_TOKEN": "verify123",
            "MISTRAL_API_KEY": "mistral123",
        }
        with patch.dict(os.environ, env_vars, clear=True), \
             patch('endpoint.security.api_keys.logger') as mock_logger:
            validate_api_keys()
            
            # Check log call includes missing_required count
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args[1]
            assert "extra" in call_kwargs
            assert call_kwargs["extra"]["missing_required"] == 0
