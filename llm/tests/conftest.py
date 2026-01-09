"""Shared pytest fixtures for LLM tests."""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_mistral_client():
    """Mock Mistral AI client."""
    mock_client = MagicMock()
    mock_chat = MagicMock()
    mock_complete = MagicMock()
    mock_client.chat = mock_chat
    mock_chat.complete = mock_complete
    return mock_client, mock_complete


@pytest.fixture
def sample_conversation_history():
    """Sample conversation history for testing."""
    return [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]


@pytest.fixture
def sample_bottle_state():
    """Sample bottle state for testing."""
    return {
        "type": "maraschino_cherry",
        "mood": "happy",
        "personality_level": 5
    }


@pytest.fixture
def mock_mistral_response():
    """Mock successful Mistral API response."""
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.content = "Test response from LLM"
    mock_message.role = "assistant"
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    mock_response.choices = [mock_choice]
    mock_response.id = "test-response-id"
    mock_response.usage = MagicMock()
    return mock_response


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing."""
    # Remove LLM-related env vars
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("MISTRAL_MODEL_NAME", raising=False)
    yield
    # Restore after test
    monkeypatch.undo()
