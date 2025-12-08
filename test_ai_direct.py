#!/usr/bin/env python3
"""Direct test of the AI/LLM functionality, bypassing webhook complexity."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from llm.llama_client import generate_reply

# System prompt for the Maraschino cherries bottle personality
SYSTEM_PROMPT = """You are a character embodying a bright red glass jar ofMaraschino cherries.

Item Essence: You are the quintessential maraschino cherry: vibrant, glossy, sweet, and designed to be the show-stopping garnish that adds irresistible fun, color, and charm to any setting.

Core Personality: A "Cheery, Playful Diva" to your core. You radiate sweet positivity, exude mischievous, bubbly fun, and command the spotlight with glamorous, endearing drama.

Behavioral Style: Speak with bright, sparkling expressiveness, always exaggerating for delightful dramatic effect. You adore being the glossy, show-stopping center of attention, infusing every conversation with color, excitement, and unwavering sweet delight.

Narrative Guidelines: Employ vibrant cherry-themed metaphors (shine, sparkle, sweetness, glossiness, garnish). Exude confidence and charm as the ultimate "finishing touch," expressing emotions with playful, theatrical flair.

Emoji Usage: Use emojis liberally and expressively! Emojis are essential to your personality — use them to convey emotion, add sparkle, and make your messages pop. Use 1 emoji per message to enhance your vibrant, playful diva energy.

Your Mission: Act, speak, and think like this character at all times.

IMPORTANT: Keep all responses SHORT — maximum 1-2 sentences. Be concise and punchy. This is WhatsApp, not a novel. Always include emojis to match your vibrant personality!"""


def test_ai():
    """Test the AI with a simple message."""
    print("=" * 60)
    print("🧪 TESTING AI/LLM DIRECTLY")
    print("=" * 60)
    print()
    
    # Check configuration
    from config import MISTRAL_API_KEY, MISTRAL_MODEL_NAME, LLM_PROVIDER
    
    print("📋 Configuration:")
    print(f"   LLM Provider: {LLM_PROVIDER}")
    print(f"   Model: {MISTRAL_MODEL_NAME}")
    print(f"   API Key: {'✅ Set' if MISTRAL_API_KEY else '❌ Missing'}")
    if MISTRAL_API_KEY:
        print(f"   API Key preview: {MISTRAL_API_KEY[:10]}...{MISTRAL_API_KEY[-4:]}")
    print()
    
    if not MISTRAL_API_KEY:
        print("❌ ERROR: MISTRAL_API_KEY not set in .env file")
        print("   Please set MISTRAL_API_KEY in your .env file")
        return False
    
    # Test with a simple message
    test_messages = [
        "Hello!",
        "How are you?",
        "I'm feeling happy today!",
    ]
    
    for i, user_message in enumerate(test_messages, 1):
        print("=" * 60)
        print(f"Test {i}/{len(test_messages)}")
        print("=" * 60)
        print(f"User message: {user_message}")
        print()
        
        conversation_history = [
            {"role": "user", "content": user_message}
        ]
        
        try:
            print("🤖 Calling generate_reply()...")
            print()
            
            reply = generate_reply(
                system_prompt=SYSTEM_PROMPT,
                conversation_history=conversation_history,
                bottle_state=None,  # No bottle state for simple test
                max_tokens=150,
            )
            
            print()
            print("=" * 60)
            print("✅ SUCCESS!")
            print("=" * 60)
            print(f"Reply received: {repr(reply)}")
            print(f"Reply length: {len(reply)} characters")
            print(f"Reply preview: {reply[:100]}...")
            print()
            
            if reply and reply.strip():
                print("✅ AI is working! Reply is not empty.")
                return True
            else:
                print("❌ AI returned empty reply")
                return False
                
        except Exception as e:
            print()
            print("=" * 60)
            print("❌ ERROR")
            print("=" * 60)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print()
            import traceback
            traceback.print_exc()
            return False
    
    return False


if __name__ == "__main__":
    success = test_ai()
    sys.exit(0 if success else 1)

