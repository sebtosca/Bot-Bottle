from __future__ import annotations

from typing import List, Dict, Any, Optional
import json
import re

from config import (
    LLM_PROVIDER,
    MISTRAL_API_KEY,
    MISTRAL_MODEL_NAME,
)
import logging

logger = logging.getLogger(__name__)


def _generate_reply_mistral(
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    bottle_state: Dict[str, Any] | None = None,
    temperature: float = 0.8,
    max_tokens: int = 150,
) -> str:
    """Generate reply using Mistral AI API.
    
    Args:
        system_prompt: The system prompt describing the bot's personality and role.
        conversation_history: List of message dicts with 'role' ('user' or 'assistant') and 'content'.
        bottle_state: Optional dict with bottle state (type, mood, personality_level).
        temperature: Sampling temperature (0.0-2.0). Higher = more creative.
        max_tokens: Maximum tokens in the response.
    
    Returns:
        The generated reply text from Mistral AI.
    
    Raises:
        RuntimeError: If MISTRAL_API_KEY is not set.
        Exception: If the API call fails.
    """
    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY is not set")
        raise RuntimeError("MISTRAL_API_KEY is required when using Mistral provider. Set it in .env file.")
    
    # Log that API key is being used (but not the value)
    logger.debug("Using Mistral API key", extra={
        "key_set": True,
        "key_length": len(MISTRAL_API_KEY) if MISTRAL_API_KEY else 0,
        "model": MISTRAL_MODEL_NAME
    })
    
    try:
        from mistralai import Mistral
    except ImportError:
        logger.error("mistralai package not installed")
        raise RuntimeError("mistralai package not installed. Run: pip install mistralai")
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as client_error:
        logger.exception("Failed to create Mistral client", extra={"error": str(client_error)})
        raise RuntimeError(f"Failed to initialize Mistral client: {client_error}")
    
    # Build the system prompt with bottle state context if provided
    full_system_prompt = system_prompt
    if bottle_state:
        state_desc = (
            f"Current bottle state: type={bottle_state.get('type', 'unknown')}, "
            f"mood={bottle_state.get('mood', 'neutral')}, "
            f"personality_level={bottle_state.get('personality_level', 0)}. "
            "Respond as this bottle."
        )
        full_system_prompt = f"{system_prompt}\n\n{state_desc}"
    
    # Build messages list: system message + conversation history
    messages = [{"role": "system", "content": full_system_prompt}] + conversation_history
    
    # Log request details
    logger.debug("Mistral AI API request", extra={
        "model": MISTRAL_MODEL_NAME,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages_count": len(messages),
        "system_prompt_preview": full_system_prompt[:100] + "..." if len(full_system_prompt) > 100 else full_system_prompt,
        "last_user_message_preview": conversation_history[-1].get('content', '')[:100] + "..." if conversation_history and len(conversation_history[-1].get('content', '')) > 100 else (conversation_history[-1].get('content', '') if conversation_history else 'N/A')
    })
    
    try:
        chat_response = client.chat.complete(
            model=MISTRAL_MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as api_error:
        logger.exception("Mistral AI API call failed", extra={
            "error_type": type(api_error).__name__,
            "error_message": str(api_error)
        })
        import traceback
        traceback.print_exc()
        raise
    
    # Log full response object structure
    logger.debug("Mistral AI API response", extra={
        "response_id": chat_response.id if hasattr(chat_response, 'id') else None,
        "choices_count": len(chat_response.choices) if chat_response.choices else 0,
        "finish_reason": chat_response.choices[0].finish_reason if chat_response.choices and len(chat_response.choices) > 0 else None,
        "usage": str(chat_response.usage) if hasattr(chat_response, 'usage') else None
    })
    
    if not chat_response.choices or len(chat_response.choices) == 0:
        logger.error("Mistral AI returned no choices in response", extra={
            "response_type": type(chat_response).__name__
        })
        return ""
    
    message = chat_response.choices[0].message
    raw_content = message.content
    
    logger.debug("Mistral AI message details", extra={
        "message_role": message.role if hasattr(message, 'role') else None,
        "content_type": type(raw_content).__name__,
        "content_length": len(str(raw_content)) if raw_content else 0
    })
    
    if raw_content is None:
        finish_reason = chat_response.choices[0].finish_reason if chat_response.choices and len(chat_response.choices) > 0 else "unknown"
        logger.warning("Mistral AI returned None for message.content", extra={
            "finish_reason": finish_reason,
            "max_tokens": max_tokens
        })
        
        # Try to get alternative content if available
        if hasattr(message, 'tool_calls') and message.tool_calls:
            logger.warning("Message has tool_calls instead of content", extra={
                "tool_calls": str(message.tool_calls)[:200] if message.tool_calls else None
            })
        if hasattr(message, 'refusal') and message.refusal:
            logger.warning("Message was refused by model", extra={
                "refusal": str(message.refusal)[:200]
            })
        
        # Raise an exception instead of returning empty string to trigger proper error handling
        raise ValueError(f"Mistral AI API returned None content (finish_reason: {finish_reason})")
    
    # Log raw response for debugging
    logger.debug("Mistral AI raw response", extra={
        "response_length": len(raw_content) if raw_content else 0,
        "response_preview": str(raw_content)[:100] + "..." if raw_content and len(str(raw_content)) > 100 else str(raw_content) if raw_content else None
    })
    
    stripped = raw_content.strip()
    if not stripped:
        logger.warning("Mistral AI response is empty or whitespace only")
    
    return stripped


def analyze_message_sentiment(user_message: str) -> Dict[str, Any]:
    """Analyze the emotion and sentiment in a user message using Mistral AI.
    
    This function uses the LLM to understand the emotional context behind
    the user's message, without relying on keyword matching.
    
    Args:
        user_message: The user's message text to analyze.
    
    Returns:
        Dictionary with sentiment analysis:
            {
                "emotion": str,  # One of: "happy", "sad", "excited", "angry", 
                                 # "surprised", "neutral", "playful", "curious", 
                                 # "content", "frustrated"
                "intensity": float,  # 0.0-1.0 (how strong the emotion is)
                "should_send_media": bool  # True if emotion is strong enough for media
            }
        Returns default neutral sentiment if analysis fails.
    """
    if not MISTRAL_API_KEY:
        logger.warning("MISTRAL_API_KEY not set, returning default sentiment")
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }
    
    if not user_message or not user_message.strip():
        return {
            "emotion": "neutral",
            "intensity": 0.2,
            "should_send_media": False
        }
    
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("mistralai package not installed, returning default sentiment")
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as client_error:
        logger.exception("Failed to create Mistral client for sentiment analysis", extra={
            "error": str(client_error)
        })
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }
    
    # Create a focused prompt for sentiment analysis
    sentiment_prompt = f"""Analyze the emotion and sentiment in this message: "{user_message}"

Return ONLY valid JSON with this exact structure:
{{
    "emotion": "one of: happy, sad, excited, angry, surprised, neutral, playful, curious, content, frustrated",
    "intensity": 0.0-1.0,
    "should_send_media": true or false
}}

The intensity should reflect how strong the emotion is (0.0 = very weak/neutral, 1.0 = very strong).
Set should_send_media to true if the emotion is strong enough (intensity > 0.5) to warrant a GIF or sticker response.

Return ONLY the JSON, no other text."""
    
    messages = [
        {"role": "system", "content": "You are an emotion analysis assistant. Always return valid JSON."},
        {"role": "user", "content": sentiment_prompt}
    ]
    
    try:
        chat_response = client.chat.complete(
            model=MISTRAL_MODEL_NAME,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=150,
        )
        
        if not chat_response.choices or len(chat_response.choices) == 0:
            logger.warning("Sentiment analysis returned no choices")
            return {
                "emotion": "neutral",
                "intensity": 0.3,
                "should_send_media": False
            }
        
        raw_content = chat_response.choices[0].message.content
        if not raw_content:
            logger.warning("Sentiment analysis returned None content")
            return {
                "emotion": "neutral",
                "intensity": 0.3,
                "should_send_media": False
            }
        
        # Extract JSON from response (handle cases where LLM adds extra text)
        content = raw_content.strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = content
        
        # Parse JSON
        try:
            sentiment_data = json.loads(json_str)
            
            # Validate and normalize the response
            emotion = sentiment_data.get("emotion", "neutral").lower()
            valid_emotions = ["happy", "sad", "excited", "angry", "surprised", "neutral", 
                            "playful", "curious", "content", "frustrated"]
            if emotion not in valid_emotions:
                emotion = "neutral"
            
            intensity = float(sentiment_data.get("intensity", 0.3))
            intensity = max(0.0, min(1.0, intensity))  # Clamp to 0.0-1.0
            
            should_send_media = bool(sentiment_data.get("should_send_media", intensity > 0.5))
            
            result = {
                "emotion": emotion,
                "intensity": intensity,
                "should_send_media": should_send_media
            }
            
            logger.debug("Sentiment analysis result", extra={
                "emotion": emotion,
                "intensity": intensity,
                "should_send_media": should_send_media
            })
            
            return result
            
        except json.JSONDecodeError as json_error:
            logger.warning("Failed to parse sentiment JSON", extra={
                "error": str(json_error),
                "raw_response_preview": content[:200] if content else None
            })
            return {
                "emotion": "neutral",
                "intensity": 0.3,
                "should_send_media": False
            }
            
    except Exception as api_error:
        logger.exception("Sentiment analysis API call failed", extra={
            "error": str(api_error)
        })
        import traceback
        traceback.print_exc()
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }


def detect_emotion_from_message(user_message: str) -> str:
    """Detect emotion from user message using Mistral AI.
    
    Analyzes the user's message to determine the appropriate emotional response.
    Returns one of: "happy", "sad", "angry", "shocked", "neutral"
    
    Args:
        user_message: The user's message text.
    
    Returns:
        Emotion string: "happy", "sad", "angry", "shocked", or "neutral"
    """
    if not MISTRAL_API_KEY:
        logger.warning("MISTRAL_API_KEY not set, defaulting to neutral emotion")
        return "neutral"
    
    try:
        from mistralai import Mistral
    except ImportError:
        logger.warning("mistralai package not installed, defaulting to neutral emotion")
        return "neutral"
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as e:
        logger.exception("Failed to create Mistral client for emotion detection", extra={
            "error": str(e)
        })
        return "neutral"
    
    # System prompt for emotion detection
    emotion_prompt = """Analysez le message de l'utilisateur et déterminez l'émotion appropriée pour la réponse.

Répondez UNIQUEMENT avec un seul mot parmi: happy, sad, angry, shocked, neutral

Règles:
- Si le message contient des insultes, des mots grossiers, ou est négatif/hostile → "angry"
- Si le message est triste, déprimant, ou exprime de la peine → "sad"
- Si le message est positif, joyeux, ou amical → "happy"
- Si le message est surprenant, choquant, ou inattendu → "shocked"
- Si le message est neutre, informatif, ou sans émotion claire → "neutral"

Répondez uniquement avec le mot, sans explication."""

    messages = [
        {"role": "system", "content": emotion_prompt},
        {"role": "user", "content": user_message}
    ]
    
    try:
        response = client.chat.complete(
            model=MISTRAL_MODEL_NAME,
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent emotion detection
            max_tokens=10,  # Just need one word
        )
        
        if response.choices and len(response.choices) > 0:
            emotion = response.choices[0].message.content.strip().lower()
            # Validate emotion
            valid_emotions = ["happy", "sad", "angry", "shocked", "neutral"]
            if emotion in valid_emotions:
                logger.debug("Emotion detected", extra={"emotion": emotion})
                return emotion
            else:
                logger.warning("Invalid emotion detected, defaulting to neutral", extra={"emotion": emotion})
                return "neutral"
        else:
            logger.warning("No response from Mistral for emotion detection, defaulting to neutral")
            return "neutral"
    except Exception as e:
        logger.exception("Error detecting emotion", extra={"error": str(e)})
        return "neutral"


def generate_reply(
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    bottle_state: Dict[str, Any] | None = None,
    temperature: float = 0.8,
    max_tokens: int = 150,
) -> str:
    """Generate reply using Mistral AI.
    
    Args:
        system_prompt: The system prompt describing the bot's personality and role.
        conversation_history: List of message dicts with 'role' ('user' or 'assistant') and 'content'.
        bottle_state: Optional dict with bottle state (type, mood, personality_level).
        temperature: Sampling temperature (0.0-2.0). Higher = more creative.
        max_tokens: Maximum tokens in the response.
    
    Returns:
        The generated reply text from Mistral AI.
    
    Raises:
        RuntimeError: If provider is not 'mistral' or required credentials are missing.
        Exception: If the API call fails.
    """
    provider = LLM_PROVIDER.lower()
    
    if provider == "mistral":
        return _generate_reply_mistral(
            system_prompt, conversation_history, bottle_state, temperature, max_tokens
        )
    else:
        raise RuntimeError(
            f"Invalid LLM_PROVIDER: {provider}. Must be 'mistral'. "
            f"Set LLM_PROVIDER=mistral in .env file."
        )

