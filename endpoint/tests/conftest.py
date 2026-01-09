"""Shared pytest fixtures for endpoint tests."""

import pytest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Generator

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from flask.testing import FlaskClient

# Import endpoint modules
from endpoint.webhook.models import JobPayload, ParsedMessage, WebhookEvent
from endpoint.webhook.queue import InMemoryQueue
from endpoint.webhook.idempotency import InMemoryIdempotencyStore
from endpoint.security.rate_limiter import InMemoryRateLimiter


@pytest.fixture(scope="session")
def project_root_path() -> Path:
    """Get project root directory."""
    return project_root


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def app() -> Flask:
    """Create Flask test application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    return app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def sample_webhook_payload() -> dict:
    """Sample WhatsApp webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550551234",
                        "phone_number_id": "PHONE_NUMBER_ID"
                    },
                    "messages": [{
                        "from": "15551234567",
                        "id": "wamid.test123",
                        "timestamp": "1234567890",
                        "type": "text",
                        "text": {
                            "body": "Hello, world!"
                        },
                        "context": {
                            "product": "00001"
                        }
                    }]
                },
                "field": "messages"
            }]
        }]
    }


@pytest.fixture
def sample_webhook_payload_status() -> dict:
    """Sample WhatsApp webhook payload for status update."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "statuses": [{
                        "id": "wamid.test123",
                        "status": "sent",
                        "timestamp": "1234567890",
                        "recipient_id": "15551234567"
                    }]
                },
                "field": "messages"
            }]
        }]
    }


@pytest.fixture
def sample_webhook_payload_test_format() -> dict:
    """Sample webhook payload in test format (direct value)."""
    return {
        "value": {
            "messaging_product": "whatsapp",
            "messages": [{
                "from": "15551234567",
                "id": "wamid.test123",
                "timestamp": "1234567890",
                "type": "text",
                "text": {
                    "body": "Test message"
                }
            }]
        }
    }


@pytest.fixture
def sample_parsed_message() -> ParsedMessage:
    """Sample parsed message."""
    return ParsedMessage(
        message_id="wamid.test123",
        from_number="15551234567",
        message_type="text",
        body="Hello, world!",
        num_media=0,
        media_type="",
        product_id="00001",
        raw_message={
            "from": "15551234567",
            "id": "wamid.test123",
            "type": "text",
            "text": {"body": "Hello, world!"}
        }
    )


@pytest.fixture
def sample_job_payload(sample_parsed_message: ParsedMessage) -> JobPayload:
    """Sample job payload."""
    import time
    return JobPayload(
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


@pytest.fixture
def message_queue() -> InMemoryQueue:
    """In-memory message queue for tests."""
    return InMemoryQueue(maxsize=100)


@pytest.fixture
def idempotency_store() -> InMemoryIdempotencyStore:
    """In-memory idempotency store for tests."""
    store = InMemoryIdempotencyStore()
    yield store
    store.clear()


@pytest.fixture
def rate_limiter() -> InMemoryRateLimiter:
    """In-memory rate limiter for tests."""
    limiter = InMemoryRateLimiter()
    yield limiter
    limiter.clear()


@pytest.fixture
def mock_whatsapp_api():
    """Mock WhatsApp API responses."""
    with patch('services.whatsapp.client.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.test123"}]
        }
        mock_response.text = '{"messages": [{"id": "wamid.test123"}]}'
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_llm():
    """Mock LLM service."""
    with patch('llm.llama_client.generate_reply') as mock_generate, \
         patch('llm.llama_client.detect_emotion_from_message') as mock_emotion:
        mock_generate.return_value = "Mocked LLM response"
        mock_emotion.return_value = "happy"
        yield {
            'generate': mock_generate,
            'emotion': mock_emotion
        }


@pytest.fixture
def mock_time():
    """Mock time for deterministic tests."""
    import time
    with patch('time.time', return_value=1234567890.0):
        yield


@pytest.fixture
def mock_random():
    """Mock random for deterministic tests."""
    import random
    with patch('random.random', return_value=0.5), \
         patch('random.choice', side_effect=lambda x: x[0] if x else None), \
         patch('random.choices', side_effect=lambda population, weights=None, k=1: [population[0]]):
        yield


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables before each test."""
    # Save original values
    original_env = {}
    env_vars_to_save = [
        'WHATSAPP_APP_SECRET',
        'WHATSAPP_VERIFY_TOKEN',
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID',
        'DATABASE_URL',
        'REDIS_URL',
        'PUBLIC_BASE_URL'
    ]
    
    for var in env_vars_to_save:
        original_env[var] = os.environ.get(var)
    
    yield
    
    # Restore original values
    for var, value in original_env.items():
        if value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = value


@pytest.fixture
def clean_env():
    """Clean environment for tests that need no env vars."""
    env_vars_to_clear = [
        'WHATSAPP_APP_SECRET',
        'WHATSAPP_VERIFY_TOKEN',
        'WHATSAPP_ACCESS_TOKEN',
        'WHATSAPP_PHONE_NUMBER_ID',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    saved = {}
    for var in env_vars_to_clear:
        saved[var] = os.environ.pop(var, None)
    
    yield
    
    for var, value in saved.items():
        if value is not None:
            os.environ[var] = value
