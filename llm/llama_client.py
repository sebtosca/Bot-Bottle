from __future__ import annotations

from typing import List, Dict, Any, Optional
import json
import re

from config import (
    LLM_PROVIDER,
    MISTRAL_API_KEY,
    MISTRAL_MODEL_NAME,
)


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
        raise RuntimeError("MISTRAL_API_KEY is required when using Mistral provider. Set it in .env file.")
    
    try:
        from mistralai import Mistral
    except ImportError:
        raise RuntimeError("mistralai package not installed. Run: pip install mistralai")
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as client_error:
        print(f"❌ Failed to create Mistral client: {client_error}")
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
    print(f"🔍 Mistral AI API Request:")
    print(f"   Model: {MISTRAL_MODEL_NAME}")
    print(f"   Temperature: {temperature}")
    print(f"   Max tokens: {max_tokens}")
    print(f"   Messages count: {len(messages)}")
    print(f"   System prompt (first 100 chars): {full_system_prompt[:100]}...")
    print(f"   Last user message: {conversation_history[-1].get('content', 'N/A')[:100] if conversation_history else 'N/A'}")
    
    try:
        chat_response = client.chat.complete(
            model=MISTRAL_MODEL_NAME,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as api_error:
        print(f"❌ Mistral AI API call failed with exception:")
        print(f"   Error type: {type(api_error).__name__}")
        print(f"   Error message: {str(api_error)}")
        import traceback
        traceback.print_exc()
        raise
    
    # Log full response object structure
    print(f"🔍 Mistral AI API Response:")
    print(f"   Response ID: {chat_response.id if hasattr(chat_response, 'id') else 'N/A'}")
    print(f"   Choices count: {len(chat_response.choices) if chat_response.choices else 0}")
    print(f"   Finish reason: {chat_response.choices[0].finish_reason if chat_response.choices and len(chat_response.choices) > 0 else 'N/A'}")
    print(f"   Usage: {chat_response.usage if hasattr(chat_response, 'usage') else 'N/A'}")
    
    if not chat_response.choices or len(chat_response.choices) == 0:
        print(f"❌ Mistral AI returned no choices in response")
        print(f"   Full response object: {chat_response}")
        return ""
    
    message = chat_response.choices[0].message
    raw_content = message.content
    
    print(f"   Message role: {message.role if hasattr(message, 'role') else 'N/A'}")
    print(f"   Message content type: {type(raw_content)}")
    print(f"   Message content value: {repr(raw_content)}")
    
    if raw_content is None:
        finish_reason = chat_response.choices[0].finish_reason if chat_response.choices and len(chat_response.choices) > 0 else "unknown"
        print(f"❌ Mistral AI returned None for message.content")
        print(f"   Finish reason: {finish_reason}")
        print(f"   This usually means:")
        if finish_reason == "length":
            print(f"      - Model hit max_tokens limit ({max_tokens}) - try increasing max_tokens")
        elif finish_reason == "content_filter":
            print(f"      - Model was stopped by content filters - try adjusting the prompt")
        elif finish_reason == "stop":
            print(f"      - Model stopped normally but returned None (unusual)")
        else:
            print(f"      - Unknown finish reason: {finish_reason}")
        print(f"   Full message object: {message}")
        print(f"   Full response object keys: {dir(chat_response)}")
        
        # Try to get alternative content if available
        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f"   ⚠️  Message has tool_calls instead of content: {message.tool_calls}")
        if hasattr(message, 'refusal') and message.refusal:
            print(f"   ⚠️  Message was refused: {message.refusal}")
        
        # Raise an exception instead of returning empty string to trigger proper error handling
        raise ValueError(f"Mistral AI API returned None content (finish_reason: {finish_reason})")
    
    # Log raw response for debugging
    print(f"🔍 Mistral AI raw response (before strip): {repr(raw_content)}")
    print(f"🔍 Mistral AI raw response length: {len(raw_content)}")
    
    stripped = raw_content.strip()
    if not stripped:
        print(f"⚠️  Mistral AI response is empty or whitespace only")
    
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
        print("⚠️  MISTRAL_API_KEY not set, returning default sentiment")
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
        print("⚠️  mistralai package not installed, returning default sentiment")
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }
    
    try:
        client = Mistral(api_key=MISTRAL_API_KEY)
    except Exception as client_error:
        print(f"⚠️  Failed to create Mistral client for sentiment analysis: {client_error}")
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
            print("⚠️  Sentiment analysis returned no choices")
            return {
                "emotion": "neutral",
                "intensity": 0.3,
                "should_send_media": False
            }
        
        raw_content = chat_response.choices[0].message.content
        if not raw_content:
            print("⚠️  Sentiment analysis returned None content")
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
            
            print(f"🔍 Sentiment Analysis Result:")
            print(f"   Emotion: {emotion}")
            print(f"   Intensity: {intensity:.2f}")
            print(f"   Should send media: {should_send_media}")
            
            return result
            
        except json.JSONDecodeError as json_error:
            print(f"⚠️  Failed to parse sentiment JSON: {json_error}")
            print(f"   Raw response: {content[:200]}")
            return {
                "emotion": "neutral",
                "intensity": 0.3,
                "should_send_media": False
            }
            
    except Exception as api_error:
        print(f"⚠️  Sentiment analysis API call failed: {api_error}")
        import traceback
        traceback.print_exc()
        return {
            "emotion": "neutral",
            "intensity": 0.3,
            "should_send_media": False
        }


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

