"""Shared pytest fixtures for WhatsApp service tests."""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_requests_post(monkeypatch):
    """Mock requests.post for WhatsApp API calls."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "messages": [{"id": "wamid.test123"}],
        "contacts": [{"wa_id": "+33684950535", "input": "+33684950535"}]
    }
    mock_response.text = json.dumps(mock_response.json.return_value)
    
    mock_post = MagicMock(return_value=mock_response)
    monkeypatch.setattr("services.whatsapp.client.requests.post", mock_post)
    return mock_post, mock_response


@pytest.fixture
def sample_whatsapp_success_response():
    """Sample successful WhatsApp API response."""
    return {
        "messages": [{"id": "wamid.HBgNMTIzNDU2Nzg5ABIREhFQSkpKSlBQUFBQUFBQUFB"}],
        "contacts": [{"wa_id": "+33684950535", "input": "+33684950535"}]
    }


@pytest.fixture
def sample_whatsapp_error_response():
    """Sample WhatsApp API error response."""
    return {
        "error": {
            "message": "(#131030) Recipient phone number not in allowed list",
            "type": "OAuthException",
            "code": 10,
            "error_data": {
                "messaging_product": "whatsapp",
                "details": "Phone number not in allowed list"
            }
        }
    }


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_PHONE_NUMBER_ID", raising=False)
    yield
    monkeypatch.undo()
