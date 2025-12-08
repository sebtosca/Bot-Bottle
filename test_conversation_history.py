#!/usr/bin/env python3
"""Test conversation history building to diagnose Mistral AI empty response issue."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import DATABASE_URL
from db.db import init_db, get_session, get_recent_interactions, get_or_create_user, get_or_create_bottle
from llm.llama_client import generate_reply

# System prompt
SYSTEM_PROMPT = """You are a character embodying a bright red glass jar ofMaraschino cherries.

Item Essence: You are the quintessential maraschino cherry: vibrant, glossy, sweet, and designed to be the show-stopping garnish that adds irresistible fun, color, and charm to any setting.

Core Personality: A "Cheery, Playful Diva" to your core. You radiate sweet positivity, exude mischievous, bubbly fun, and command the spotlight with glamorous, endearing drama.

Behavioral Style: Speak with bright, sparkling expressiveness, always exaggerating for delightful dramatic effect. You adore being the glossy, show-stopping center of attention, infusing every conversation with color, excitement, and unwavering sweet delight.

Narrative Guidelines: Employ vibrant cherry-themed metaphors (shine, sparkle, sweetness, glossiness, garnish). Exude confidence and charm as the ultimate "finishing touch," expressing emotions with playful, theatrical flair.

Emoji Usage: Use emojis liberally and expressively! Emojis are essential to your personality — use them to convey emotion, add sparkle, and make your messages pop. Use 1 emoji per message to enhance your vibrant, playful diva energy.

Your Mission: Act, speak, and think like this character at all times.

IMPORTANT: Keep all responses SHORT — maximum 1-2 sentences. Be concise and punchy. This is WhatsApp, not a novel. Always include emojis to match your vibrant personality!"""


def test_conversation_history():
    """Test how conversation history is built from database."""
    print("=" * 60)
    print("🧪 TESTING CONVERSATION HISTORY")
    print("=" * 60)
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set - cannot test conversation history")
        return False
    
    test_number = "33684950535"
    
    try:
        # Initialize database
        init_db()
        session = get_session()
        
        # Get user and bottle
        user = get_or_create_user(session, test_number)
        bottle = get_or_create_bottle(session, user.id, bottle_type="maraschino_cherry")
        
        # Get recent interactions
        recent_interactions = get_recent_interactions(session, bottle.id, limit=8)
        
        print(f"📊 Database Interactions: {len(recent_interactions)} found")
        print()
        
        # Build conversation history like endpoint does
        conversation_history = []
        for i, inter in enumerate(recent_interactions, 1):
            role = "user" if inter.from_user == "true" else "assistant"
            content = inter.content or ""
            
            print(f"Interaction {i}:")
            print(f"   from_user (raw): {repr(inter.from_user)}")
            print(f"   from_user (type): {type(inter.from_user)}")
            print(f"   role: {role}")
            print(f"   content (raw): {repr(content)}")
            print(f"   content (type): {type(content)}")
            print(f"   content length: {len(content) if content else 0}")
            print()
            
            # Check for issues
            if not content or not content.strip():
                print(f"   ⚠️  WARNING: Empty or whitespace-only content!")
            
            conversation_history.append({"role": role, "content": content})
        
        print("=" * 60)
        print("📝 Built Conversation History:")
        print("=" * 60)
        for i, msg in enumerate(conversation_history, 1):
            print(f"{i}. {msg['role']}: {repr(msg['content'][:50])}...")
        print()
        
        # Validate conversation history
        print("=" * 60)
        print("🔍 Validating Conversation History:")
        print("=" * 60)
        valid_history = []
        for item in conversation_history:
            if isinstance(item, dict) and "role" in item and "content" in item:
                if item["content"] and item["content"].strip():
                    valid_history.append(item)
                else:
                    print(f"⚠️  Skipping empty content: {item}")
            else:
                print(f"⚠️  Invalid item: {item}")
        
        print(f"Valid messages: {len(valid_history)}")
        print()
        
        if not valid_history:
            print("❌ No valid conversation history!")
            return False
        
        # CRITICAL: Ensure conversation history ends with a user message
        # Mistral AI needs the last message to be from the user to generate a reply
        current_user_message = "hey"  # Simulate current message
        if not valid_history or valid_history[-1]["role"] != "user":
            print(f"⚠️  History ends with assistant, adding current user message: {current_user_message}")
            valid_history.append({"role": "user", "content": current_user_message})
        elif valid_history[-1]["content"] != current_user_message:
            print(f"⚠️  Last user message differs, adding current: {current_user_message}")
            valid_history.append({"role": "user", "content": current_user_message})
        
        # Test with Mistral AI
        print("=" * 60)
        print("🤖 Testing with Mistral AI:")
        print("=" * 60)
        print(f"Valid history count: {len(valid_history)}")
        print(f"Last message role: {valid_history[-1]['role']}")
        print(f"Last message: {valid_history[-1]['content'][:50]}...")
        print()
        
        reply = generate_reply(
            system_prompt=SYSTEM_PROMPT,
            conversation_history=valid_history,
            bottle_state=None,
            max_tokens=150,
        )
        
        print()
        print("=" * 60)
        if reply and reply.strip():
            print("✅ SUCCESS - Got reply from Mistral AI")
            print(f"Reply: {reply}")
            return True
        else:
            print("❌ FAILED - Mistral AI returned empty reply")
            print(f"Reply: {repr(reply)}")
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    success = test_conversation_history()
    sys.exit(0 if success else 1)

