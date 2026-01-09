"""Unit tests for security validation module."""

import pytest
from endpoint.security.validation import (
    ValidationError,
    FieldValidator,
    SchemaValidator,
    sanitize_string,
    sanitize_filename,
    validate_phone_number,
    validate_whatsapp_message_id,
    validate_product_id
)


class TestSanitizeString:
    """Tests for sanitize_string function."""
    
    def test_sanitize_normal_string(self):
        """Test sanitizing normal string."""
        result = sanitize_string("Hello, world!")
        
        assert result == "Hello, world!"
    
    def test_sanitize_removes_control_chars(self):
        """Test sanitizing removes control characters."""
        result = sanitize_string("Hello\x00\x01world")
        
        assert "\x00" not in result
        assert "\x01" not in result
    
    def test_sanitize_trims_whitespace(self):
        """Test sanitizing trims whitespace."""
        result = sanitize_string("  Hello, world!  ")
        
        assert result == "Hello, world!"
    
    def test_sanitize_truncates_long_string(self):
        """Test sanitizing truncates long string."""
        long_string = "a" * 200
        result = sanitize_string(long_string, max_length=100)
        
        assert len(result) == 100
        assert result == "a" * 100
    
    def test_sanitize_preserves_newlines(self):
        """Test sanitizing preserves newlines."""
        result = sanitize_string("Hello\nworld")
        
        assert "\n" in result
    
    def test_sanitize_converts_non_string(self):
        """Test sanitizing converts non-string to string."""
        result = sanitize_string(12345)
        
        assert result == "12345"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""
    
    def test_sanitize_valid_filename(self):
        """Test sanitizing valid filename."""
        result = sanitize_filename("happy_cherry.webp")
        
        assert result == "happy_cherry.webp"
    
    def test_sanitize_removes_path_traversal(self):
        """Test sanitizing rejects path traversal."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("../etc/passwd")
    
    def test_sanitize_removes_slashes(self):
        """Test sanitizing rejects slashes."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("folder/file.webp")
    
    def test_sanitize_removes_backslashes(self):
        """Test sanitizing rejects backslashes."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("folder\\file.webp")
    
    def test_sanitize_rejects_colon(self):
        """Test sanitizing rejects colon."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("file:name.webp")
    
    def test_sanitize_removes_control_chars(self):
        """Test sanitizing removes control characters."""
        result = sanitize_filename("file\x00\x01.webp")
        
        assert "\x00" not in result
        assert "\x01" not in result
    
    def test_sanitize_rejects_empty(self):
        """Test sanitizing rejects empty filename."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("")
    
    def test_sanitize_rejects_whitespace_only(self):
        """Test sanitizing rejects whitespace-only filename."""
        with pytest.raises(ValidationError, match="Invalid filename"):
            sanitize_filename("   ")
    
    def test_sanitize_rejects_non_string(self):
        """Test sanitizing rejects non-string input."""
        with pytest.raises(ValidationError, match="must be a string"):
            sanitize_filename(12345)
    
    def test_sanitize_trims_whitespace(self):
        """Test sanitizing trims whitespace."""
        result = sanitize_filename("  file.webp  ")
        
        assert result == "file.webp"


class TestValidatePhoneNumber:
    """Tests for validate_phone_number function."""
    
    def test_validate_valid_phone(self):
        """Test validating valid phone number."""
        assert validate_phone_number("+15551234567") is True
    
    def test_validate_invalid_no_plus(self):
        """Test validating phone without plus."""
        assert validate_phone_number("15551234567") is False
    
    def test_validate_invalid_too_short(self):
        """Test validating phone that's too short."""
        assert validate_phone_number("+1") is False
    
    def test_validate_invalid_too_long(self):
        """Test validating phone that's too long."""
        assert validate_phone_number("+123456789012345678") is False
    
    def test_validate_invalid_chars(self):
        """Test validating phone with invalid characters."""
        assert validate_phone_number("+1-555-123-4567") is False
    
    def test_validate_invalid_starts_with_zero(self):
        """Test validating phone starting with zero."""
        assert validate_phone_number("+05551234567") is False


class TestValidateWhatsAppMessageId:
    """Tests for validate_whatsapp_message_id function."""
    
    def test_validate_valid_message_id(self):
        """Test validating valid message ID."""
        assert validate_whatsapp_message_id("wamid.test123") is True
    
    def test_validate_message_id_with_dots(self):
        """Test validating message ID with dots."""
        assert validate_whatsapp_message_id("wamid.HASH.test123") is True
    
    def test_validate_message_id_with_underscores(self):
        """Test validating message ID with underscores."""
        assert validate_whatsapp_message_id("wamid_test_123") is True
    
    def test_validate_invalid_too_short(self):
        """Test validating message ID that's too short."""
        assert validate_whatsapp_message_id("abc") is False
    
    def test_validate_invalid_too_long(self):
        """Test validating message ID that's too long."""
        assert validate_whatsapp_message_id("a" * 101) is False
    
    def test_validate_invalid_chars(self):
        """Test validating message ID with invalid characters."""
        assert validate_whatsapp_message_id("wamid@test#123") is False
    
    def test_validate_invalid_type(self):
        """Test validating non-string message ID."""
        assert validate_whatsapp_message_id(12345) is False


class TestValidateProductId:
    """Tests for validate_product_id function."""
    
    def test_validate_valid_product_id(self):
        """Test validating valid product ID."""
        assert validate_product_id("00001") is True
        assert validate_product_id("00002") is True
        assert validate_product_id("12345") is True
    
    def test_validate_invalid_wrong_length(self):
        """Test validating product ID with wrong length."""
        assert validate_product_id("0001") is False  # Too short
        assert validate_product_id("000001") is False  # Too long
    
    def test_validate_invalid_non_digits(self):
        """Test validating product ID with non-digits."""
        assert validate_product_id("0000a") is False
        assert validate_product_id("abcde") is False
    
    def test_validate_invalid_type(self):
        """Test validating non-string product ID."""
        assert validate_product_id(1) is False  # Integer, not string


class TestSchemaValidator:
    """Tests for SchemaValidator class."""
    
    def test_validate_valid_data(self):
        """Test validating valid data."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str),
            FieldValidator("age", required=False, field_type=int)
        ])
        
        data = {"name": "John", "age": 30}
        result = schema.validate(data)
        
        assert result["name"] == "John"
        assert result["age"] == 30
    
    def test_validate_missing_required_field(self):
        """Test validating data with missing required field."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str)
        ])
        
        with pytest.raises(ValidationError, match="Missing required field"):
            schema.validate({})
    
    def test_validate_wrong_type(self):
        """Test validating data with wrong type."""
        schema = SchemaValidator([
            FieldValidator("age", required=True, field_type=int)
        ])
        
        with pytest.raises(ValidationError, match="must be int"):
            schema.validate({"age": "thirty"})
    
    def test_validate_string_length(self):
        """Test validating string length constraints."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str, min_length=3, max_length=10)
        ])
        
        # Too short
        with pytest.raises(ValidationError, match="at least"):
            schema.validate({"name": "ab"})
        
        # Too long
        with pytest.raises(ValidationError, match="at most"):
            schema.validate({"name": "a" * 11})
        
        # Valid
        result = schema.validate({"name": "John"})
        assert result["name"] == "John"
    
    def test_validate_pattern(self):
        """Test validating pattern."""
        schema = SchemaValidator([
            FieldValidator("email", required=True, field_type=str, pattern=r"^[^@]+@[^@]+\.[^@]+$")
        ])
        
        # Invalid pattern
        with pytest.raises(ValidationError, match="not in the expected format"):
            schema.validate({"email": "not-an-email"})
        
        # Valid pattern
        result = schema.validate({"email": "test@example.com"})
        assert result["email"] == "test@example.com"
    
    def test_validate_allowed_values(self):
        """Test validating allowed values."""
        schema = SchemaValidator([
            FieldValidator("status", required=True, field_type=str, allowed_values=["active", "inactive"])
        ])
        
        # Invalid value
        with pytest.raises(ValidationError, match="invalid value"):
            schema.validate({"status": "unknown"})
        
        # Valid value
        result = schema.validate({"status": "active"})
        assert result["status"] == "active"
    
    def test_validate_strict_mode(self):
        """Test strict mode rejects unexpected fields."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str)
        ], strict=True)
        
        with pytest.raises(ValidationError, match="Unexpected fields"):
            schema.validate({"name": "John", "extra": "field"})
    
    def test_validate_non_strict_mode(self):
        """Test non-strict mode allows extra fields."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str)
        ], strict=False)
        
        result = schema.validate({"name": "John", "extra": "field"})
        assert result["name"] == "John"
        # Extra field is not included in validated result
        assert "extra" not in result
    
    def test_validate_invalid_payload_type(self):
        """Test validating non-dict payload."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str)
        ])
        
        with pytest.raises(ValidationError, match="Invalid payload"):
            schema.validate("not a dict")
        
        with pytest.raises(ValidationError, match="Invalid payload"):
            schema.validate([])
    
    def test_validate_custom_validator(self):
        """Test validating with custom validator function."""
        def is_positive(value):
            return value > 0
        
        schema = SchemaValidator([
            FieldValidator("age", required=True, field_type=int, custom_validator=is_positive)
        ])
        
        # Valid
        result = schema.validate({"age": 25})
        assert result["age"] == 25
        
        # Invalid (custom validator returns False)
        with pytest.raises(ValidationError, match="failed validation"):
            schema.validate({"age": -5})
    
    def test_validate_custom_validator_raises_validation_error(self):
        """Test custom validator that raises ValidationError."""
        def custom_check(value):
            if value == "forbidden":
                raise ValidationError("This value is forbidden", field="name")
            return True
        
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str, custom_validator=custom_check)
        ])
        
        # Valid
        result = schema.validate({"name": "allowed"})
        assert result["name"] == "allowed"
        
        # Invalid (custom validator raises ValidationError)
        with pytest.raises(ValidationError, match="forbidden"):
            schema.validate({"name": "forbidden"})
    
    def test_validate_custom_validator_raises_other_exception(self):
        """Test custom validator that raises non-ValidationError."""
        def custom_check(value):
            if value == "error":
                raise ValueError("Something went wrong")
            return True
        
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str, custom_validator=custom_check)
        ])
        
        # Exception is caught and converted to ValidationError
        with pytest.raises(ValidationError, match="failed validation"):
            schema.validate({"name": "error"})
    
    def test_validate_sanitizer(self):
        """Test validating with sanitizer function."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str, sanitizer=sanitize_string)
        ])
        
        # Sanitizer removes control chars and trims
        result = schema.validate({"name": "  Hello\x00World  "})
        assert result["name"] == "HelloWorld"
    
    def test_validate_optional_field(self):
        """Test validating optional field that is None."""
        schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str),
            FieldValidator("age", required=False, field_type=int)
        ])
        
        # Optional field can be None
        result = schema.validate({"name": "John"})
        assert result["name"] == "John"
        assert "age" not in result
        
        # Optional field can be provided
        result = schema.validate({"name": "John", "age": 30})
        assert result["age"] == 30
    
    def test_validate_pattern_on_non_string(self):
        """Test pattern validation only applies to strings."""
        schema = SchemaValidator([
            FieldValidator("id", required=True, field_type=int, pattern=r"\d+")
        ])
        
        # Pattern is ignored for non-string types
        result = schema.validate({"id": 12345})
        assert result["id"] == 12345
