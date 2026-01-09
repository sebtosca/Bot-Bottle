"""Integration tests for LLM client."""

import pytest
import os
from unittest.mock import patch, MagicMock
from llm.llama_client import (
    generate_reply,
    analyze_message_sentiment,
    detect_emotion_from_message,
)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("MISTRAL_API_KEY"),
    reason="MISTRAL_API_KEY not set - skipping integration test"
)
class TestLLMIntegration:
    """Integration tests for LLM client with real API (if available)."""
    
    def test_generate_reply_integration(self, sample_conversation_history):
        """Test generating reply with real API (if key available)."""
        result = generate_reply(
            "You are a helpful assistant. Be brief.",
            sample_conversation_history,
            None,
            temperature=0.7,
            max_tokens=50
        )
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_analyze_sentiment_integration(self):
        """Test sentiment analysis with real API (if key available)."""
        result = analyze_message_sentiment("I'm so happy today!")
        
        assert "emotion" in result
        assert "intensity" in result
        assert "should_send_media" in result
        assert result["emotion"] in ["happy", "sad", "excited", "angry", "surprised", 
                                    "neutral", "playful", "curious", "content", "frustrated"]
        assert 0.0 <= result["intensity"] <= 1.0
        assert isinstance(result["should_send_media"], bool)
    
    def test_detect_emotion_integration(self):
        """Test emotion detection with real API (if key available)."""
        result = detect_emotion_from_message("I'm so happy!")
        
        assert result in ["happy", "sad", "angry", "shocked", "neutral"]


@pytest.mark.integration
class TestLLMIntegrationMocked:
    """Integration tests for LLM client with mocked API."""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_full_reply_flow(self, mock_mistral_class, sample_conversation_history, sample_bottle_state):
        """Test full reply generation flow."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Integration test response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = generate_reply(
            "System prompt",
            sample_conversation_history,
            sample_bottle_state
        )
        
        assert result == "Integration test response"
        # Verify API was called with correct parameters
        assert mock_complete.called
        call_kwargs = mock_complete.call_args[1]
        assert "messages" in call_kwargs
        assert len(call_kwargs["messages"]) > 0
