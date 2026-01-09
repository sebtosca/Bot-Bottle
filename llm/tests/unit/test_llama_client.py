"""Unit tests for LLM client (llama_client.py)."""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from llm.llama_client import (
    _generate_reply_mistral,
    analyze_message_sentiment,
    detect_emotion_from_message,
    generate_reply,
)


@pytest.mark.unit
class TestGenerateReplyMistral:
    """Tests for _generate_reply_mistral function."""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_success(self, mock_mistral_class, sample_conversation_history, sample_bottle_state):
        """Test generating reply successfully."""
        # Setup mock client
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        # Setup mock response
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Test response from LLM"
        mock_choice.message = mock_message
        mock_choice.finish_reason = "stop"
        mock_response.choices = [mock_choice]
        mock_response.id = "test-id"
        mock_complete.return_value = mock_response
        
        result = _generate_reply_mistral(
            "You are a helpful assistant",
            sample_conversation_history,
            sample_bottle_state,
            temperature=0.8,
            max_tokens=150
        )
        
        assert result == "Test response from LLM"
        mock_complete.assert_called_once()
        call_kwargs = mock_complete.call_args[1]
        assert call_kwargs["model"] == "mistral-small"
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 150
    
    @patch('llm.llama_client.MISTRAL_API_KEY', None)
    def test_generate_reply_no_api_key(self):
        """Test generating reply without API key raises error."""
        with pytest.raises(RuntimeError, match="MISTRAL_API_KEY is required"):
            _generate_reply_mistral(
                "System prompt",
                [{"role": "user", "content": "Hello"}],
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_with_bottle_state(self, mock_mistral_class, sample_conversation_history, sample_bottle_state):
        """Test generating reply with bottle state context."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        _generate_reply_mistral(
            "System prompt",
            sample_conversation_history,
            sample_bottle_state
        )
        
        # Verify system prompt includes bottle state
        call_args = mock_complete.call_args[1]
        messages = call_args["messages"]
        system_message = messages[0]
        assert "bottle state" in system_message["content"].lower()
        assert "happy" in system_message["content"]
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_no_choices(self, mock_mistral_class, sample_conversation_history):
        """Test handling response with no choices."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = []
        mock_complete.return_value = mock_response
        
        result = _generate_reply_mistral(
            "System prompt",
            sample_conversation_history,
            None
        )
        
        assert result == ""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_none_content(self, mock_mistral_class, sample_conversation_history):
        """Test handling response with None content."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice.message = mock_message
        mock_choice.finish_reason = "length"
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        with pytest.raises(ValueError, match="returned None content"):
            _generate_reply_mistral(
                "System prompt",
                sample_conversation_history,
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_api_error(self, mock_mistral_class, sample_conversation_history):
        """Test handling API error."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_complete.side_effect = Exception("API error")
        
        with pytest.raises(Exception, match="API error"):
            _generate_reply_mistral(
                "System prompt",
                sample_conversation_history,
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    def test_generate_reply_mistral_not_installed(self):
        """Test handling when mistralai package is not installed."""
        with patch.dict('sys.modules', {'mistralai': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'mistralai'")):
                with pytest.raises(RuntimeError, match="mistralai package not installed"):
                    _generate_reply_mistral(
                        "System prompt",
                        [{"role": "user", "content": "Hello"}],
                        None
                    )


@pytest.mark.unit
class TestAnalyzeMessageSentiment:
    """Tests for analyze_message_sentiment function."""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_analyze_sentiment_success(self, mock_mistral_class):
        """Test sentiment analysis successfully."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "emotion": "happy",
            "intensity": 0.8,
            "should_send_media": True
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = analyze_message_sentiment("I'm so happy today!")
        
        assert result["emotion"] == "happy"
        assert result["intensity"] == 0.8
        assert result["should_send_media"] is True
    
    @patch('llm.llama_client.MISTRAL_API_KEY', None)
    def test_analyze_sentiment_no_api_key(self):
        """Test sentiment analysis without API key returns default."""
        result = analyze_message_sentiment("Hello")
        
        assert result["emotion"] == "neutral"
        assert result["intensity"] == 0.3
        assert result["should_send_media"] is False
    
    def test_analyze_sentiment_empty_message(self):
        """Test sentiment analysis with empty message."""
        result = analyze_message_sentiment("")
        
        assert result["emotion"] == "neutral"
        assert result["intensity"] == 0.2
        assert result["should_send_media"] is False
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_analyze_sentiment_invalid_json(self, mock_mistral_class):
        """Test sentiment analysis with invalid JSON response."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "This is not JSON"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = analyze_message_sentiment("Hello")
        
        # Should fallback to default
        assert result["emotion"] == "neutral"
        assert result["intensity"] == 0.3
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_analyze_sentiment_invalid_emotion(self, mock_mistral_class):
        """Test sentiment analysis with invalid emotion value."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "emotion": "invalid_emotion",
            "intensity": 0.8,
            "should_send_media": True
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = analyze_message_sentiment("Hello")
        
        # Should normalize to neutral
        assert result["emotion"] == "neutral"
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_analyze_sentiment_intensity_clamping(self, mock_mistral_class):
        """Test sentiment analysis clamps intensity to 0.0-1.0."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "emotion": "happy",
            "intensity": 1.5,  # Out of range
            "should_send_media": True
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = analyze_message_sentiment("Hello")
        
        assert result["intensity"] == 1.0  # Clamped
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_analyze_sentiment_json_extraction(self, mock_mistral_class):
        """Test sentiment analysis extracts JSON from text response."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        # LLM might add extra text around JSON
        mock_message.content = "Here's the analysis: {\"emotion\": \"happy\", \"intensity\": 0.8, \"should_send_media\": true}"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = analyze_message_sentiment("Hello")
        
        assert result["emotion"] == "happy"
        assert result["intensity"] == 0.8


@pytest.mark.unit
class TestDetectEmotionFromMessage:
    """Tests for detect_emotion_from_message function."""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_detect_emotion_success(self, mock_mistral_class):
        """Test emotion detection successfully."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "happy"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = detect_emotion_from_message("I'm so happy!")
        
        assert result == "happy"
    
    @patch('llm.llama_client.MISTRAL_API_KEY', None)
    def test_detect_emotion_no_api_key(self):
        """Test emotion detection without API key returns neutral."""
        result = detect_emotion_from_message("Hello")
        
        assert result == "neutral"
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_detect_emotion_invalid_emotion(self, mock_mistral_class):
        """Test emotion detection with invalid emotion value."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "invalid_emotion"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = detect_emotion_from_message("Hello")
        
        # Should default to neutral
        assert result == "neutral"
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_detect_emotion_no_choices(self, mock_mistral_class):
        """Test emotion detection with no choices in response."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = []
        mock_complete.return_value = mock_response
        
        result = detect_emotion_from_message("Hello")
        
        assert result == "neutral"
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_detect_emotion_api_error(self, mock_mistral_class):
        """Test emotion detection handles API errors."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_complete.side_effect = Exception("API error")
        
        result = detect_emotion_from_message("Hello")
        
        # Should return neutral on error
        assert result == "neutral"


@pytest.mark.unit
class TestGenerateReply:
    """Tests for generate_reply function."""
    
    @patch('llm.llama_client.LLM_PROVIDER', 'mistral')
    @patch('llm.llama_client._generate_reply_mistral')
    def test_generate_reply_mistral_provider(self, mock_generate):
        """Test generate_reply with mistral provider."""
        mock_generate.return_value = "Test response"
        
        result = generate_reply(
            "System prompt",
            [{"role": "user", "content": "Hello"}],
            None
        )
        
        assert result == "Test response"
        mock_generate.assert_called_once()
    
    @patch('llm.llama_client.LLM_PROVIDER', 'invalid')
    def test_generate_reply_invalid_provider(self):
        """Test generate_reply with invalid provider raises error."""
        with pytest.raises(RuntimeError, match="Invalid LLM_PROVIDER"):
            generate_reply(
                "System prompt",
                [{"role": "user", "content": "Hello"}],
                None
            )
    
    @patch('llm.llama_client.LLM_PROVIDER', 'MISTRAL')  # Test case insensitive
    @patch('llm.llama_client._generate_reply_mistral')
    def test_generate_reply_case_insensitive(self, mock_generate):
        """Test generate_reply is case insensitive."""
        mock_generate.return_value = "Test response"
        
        result = generate_reply(
            "System prompt",
            [{"role": "user", "content": "Hello"}],
            None
        )
        
        assert result == "Test response"


@pytest.mark.unit
class TestGenerateReplyMistralEdgeCases:
    """Additional edge case tests for _generate_reply_mistral."""
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_empty_stripped_response(self, mock_mistral_class, sample_conversation_history):
        """Test handling empty or whitespace-only response."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "   "  # Only whitespace
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = _generate_reply_mistral(
            "System prompt",
            sample_conversation_history,
            None
        )
        
        assert result == ""  # Should return empty string after strip
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_client_init_error(self, mock_mistral_class, sample_conversation_history):
        """Test handling client initialization error."""
        mock_mistral_class.side_effect = Exception("Failed to initialize client")
        
        with pytest.raises(RuntimeError, match="Failed to initialize Mistral client"):
            _generate_reply_mistral(
                "System prompt",
                sample_conversation_history,
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_none_content_with_tool_calls(self, mock_mistral_class, sample_conversation_history):
        """Test handling None content with tool_calls attribute."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_message.tool_calls = [{"type": "function", "function": {"name": "test"}}]
        mock_choice.message = mock_message
        mock_choice.finish_reason = "tool_calls"
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        with pytest.raises(ValueError, match="returned None content"):
            _generate_reply_mistral(
                "System prompt",
                sample_conversation_history,
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_none_content_with_refusal(self, mock_mistral_class, sample_conversation_history):
        """Test handling None content with refusal attribute."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_message.refusal = "Content was refused"
        mock_choice.message = mock_message
        mock_choice.finish_reason = "refusal"
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        with pytest.raises(ValueError, match="returned None content"):
            _generate_reply_mistral(
                "System prompt",
                sample_conversation_history,
                None
            )
    
    @patch('llm.llama_client.MISTRAL_API_KEY', 'test_api_key')
    @patch('llm.llama_client.MISTRAL_MODEL_NAME', 'mistral-small')
    @patch('mistralai.Mistral')
    def test_generate_reply_without_bottle_state(self, mock_mistral_class, sample_conversation_history):
        """Test generating reply without bottle state."""
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_complete = MagicMock()
        mock_client.chat = mock_chat
        mock_chat.complete = mock_complete
        mock_mistral_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_complete.return_value = mock_response
        
        result = _generate_reply_mistral(
            "System prompt",
            sample_conversation_history,
            None  # No bottle state
        )
        
        assert result == "Response"
        # Verify system prompt doesn't include bottle state
        call_args = mock_complete.call_args[1]
        messages = call_args["messages"]
        system_message = messages[0]
        assert "bottle state" not in system_message["content"].lower()
