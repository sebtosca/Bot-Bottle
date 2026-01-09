"""Integration tests for security validation module."""

import pytest
from flask import Flask, request, jsonify
from endpoint.security.validation import (
    ValidationError,
    FieldValidator,
    SchemaValidator,
    sanitize_string,
    sanitize_filename,
    validate_phone_number,
    validate_whatsapp_message_id,
    validate_product_id,
)


class TestValidationIntegration:
    """Integration tests for validation in Flask context."""
    
    def test_sanitize_filename_in_route(self, app):
        """Test sanitize_filename used in a route."""
        @app.route('/file/<filename>')
        def get_file(filename):
            try:
                safe_name = sanitize_filename(filename)
                return {"filename": safe_name}, 200
            except ValidationError as e:
                return {"error": str(e)}, 400
        
        client = app.test_client()
        
        # Valid filename
        response = client.get('/file/happy_cherry.webp')
        assert response.status_code == 200
        data = response.get_json()
        assert data["filename"] == "happy_cherry.webp"
        
        # Invalid filename (starts with dot - fails regex but Flask passes it to handler)
        response = client.get('/file/.hidden_file.webp')
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        
        # Invalid filename (whitespace only - fails after trimming)
        # URL encode spaces to avoid Flask issues
        from urllib.parse import quote
        response = client.get(f'/file/{quote("   ", safe="")}')
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
    
    def test_validate_phone_in_route(self, app):
        """Test validate_phone_number used in a route."""
        @app.route('/contact', methods=['POST'])
        def contact():
            data = request.get_json() or {}
            phone = data.get('phone')
            
            if not validate_phone_number(phone):
                return {"error": "Invalid phone number"}, 400
            
            return {"status": "ok", "phone": phone}, 200
        
        client = app.test_client()
        
        # Valid phone
        response = client.post('/contact', json={"phone": "+15551234567"})
        assert response.status_code == 200
        
        # Invalid phone
        response = client.post('/contact', json={"phone": "15551234567"})
        assert response.status_code == 400
    
    def test_schema_validator_in_route(self, app):
        """Test SchemaValidator used in a route."""
        user_schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str, min_length=1, max_length=100),
            FieldValidator("email", required=True, field_type=str, pattern=r"^[^@]+@[^@]+\.[^@]+$"),
            FieldValidator("age", required=False, field_type=int)
        ])
        
        @app.route('/register', methods=['POST'])
        def register():
            try:
                data = request.get_json() or {}
                validated = user_schema.validate(data)
                return {"status": "ok", "user": validated}, 201
            except ValidationError as e:
                return {"error": e.message, "field": e.field}, 400
        
        client = app.test_client()
        
        # Valid data
        response = client.post('/register', json={
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["user"]["name"] == "John Doe"
        
        # Missing required field
        response = client.post('/register', json={"email": "john@example.com"})
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert data["field"] == "name"
        
        # Invalid email pattern
        response = client.post('/register', json={
            "name": "John Doe",
            "email": "not-an-email"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["field"] == "email"
        
        # Wrong type
        response = client.post('/register', json={
            "name": "John Doe",
            "email": "john@example.com",
            "age": "thirty"
        })
        assert response.status_code == 400
        data = response.get_json()
        assert data["field"] == "age"
    
    def test_validate_product_id_in_route(self, app):
        """Test validate_product_id used in a route."""
        @app.route('/product/<product_id>')
        def get_product(product_id):
            if not validate_product_id(product_id):
                return {"error": "Invalid product ID"}, 400
            
            return {"product_id": product_id}, 200
        
        client = app.test_client()
        
        # Valid product ID
        response = client.get('/product/00001')
        assert response.status_code == 200
        
        # Invalid product ID
        response = client.get('/product/0001')
        assert response.status_code == 400
    
    def test_validate_whatsapp_message_id_in_route(self, app):
        """Test validate_whatsapp_message_id used in a route."""
        @app.route('/message/<msg_id>')
        def get_message(msg_id):
            if not validate_whatsapp_message_id(msg_id):
                return {"error": "Invalid message ID"}, 400
            
            return {"message_id": msg_id}, 200
        
        client = app.test_client()
        
        # Valid message ID
        response = client.get('/message/wamid.test123')
        assert response.status_code == 200
        
        # Invalid message ID (too short)
        response = client.get('/message/abc')
        assert response.status_code == 400
    
    def test_sanitize_string_in_route(self, app):
        """Test sanitize_string used in a route."""
        @app.route('/comment', methods=['POST'])
        def add_comment():
            data = request.get_json() or {}
            text = data.get('text', '')
            
            # Sanitize with max length
            sanitized = sanitize_string(text, max_length=100)
            return {"comment": sanitized}, 200
        
        client = app.test_client()
        
        # Normal text
        response = client.post('/comment', json={"text": "Hello, world!"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["comment"] == "Hello, world!"
        
        # Text with control chars
        response = client.post('/comment', json={"text": "Hello\x00World"})
        assert response.status_code == 200
        data = response.get_json()
        assert "\x00" not in data["comment"]
        
        # Long text (truncated)
        long_text = "a" * 200
        response = client.post('/comment', json={"text": long_text})
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["comment"]) == 100
    
    def test_schema_validator_strict_mode_in_route(self, app):
        """Test SchemaValidator strict mode in a route."""
        strict_schema = SchemaValidator([
            FieldValidator("name", required=True, field_type=str)
        ], strict=True)
        
        @app.route('/strict', methods=['POST'])
        def strict_endpoint():
            try:
                data = request.get_json() or {}
                validated = strict_schema.validate(data)
                return {"status": "ok"}, 200
            except ValidationError as e:
                return {"error": e.message}, 400
        
        client = app.test_client()
        
        # Valid data
        response = client.post('/strict', json={"name": "John"})
        assert response.status_code == 200
        
        # Extra field (strict mode rejects)
        response = client.post('/strict', json={"name": "John", "extra": "field"})
        assert response.status_code == 400
        data = response.get_json()
        assert "Unexpected fields" in data["error"]
    
    def test_schema_validator_with_sanitizer(self, app):
        """Test SchemaValidator with sanitizer in a route."""
        schema = SchemaValidator([
            FieldValidator("username", required=True, field_type=str, sanitizer=sanitize_string)
        ])
        
        @app.route('/user', methods=['POST'])
        def create_user():
            try:
                data = request.get_json() or {}
                validated = schema.validate(data)
                return {"username": validated["username"]}, 200
            except ValidationError as e:
                return {"error": e.message}, 400
        
        client = app.test_client()
        
        # Username with control chars gets sanitized
        response = client.post('/user', json={"username": "  user\x00name  "})
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == "username"  # Trimmed and control chars removed
    
    def test_validation_error_fields(self, app):
        """Test ValidationError field attribute is preserved."""
        schema = SchemaValidator([
            FieldValidator("email", required=True, field_type=str, pattern=r"^[^@]+@[^@]+\.[^@]+$")
        ])
        
        @app.route('/validate', methods=['POST'])
        def validate():
            try:
                data = request.get_json() or {}
                schema.validate(data)
                return {"status": "ok"}, 200
            except ValidationError as e:
                return {"error": e.message, "field": e.field}, 400
        
        client = app.test_client()
        
        response = client.post('/validate', json={"email": "invalid"})
        assert response.status_code == 400
        data = response.get_json()
        assert data["field"] == "email"
        assert "error" in data
