#!/usr/bin/env python3
"""Test script for the feeding game mechanics.

This script tests:
- Game initialization
- Name collection
- Emoji feeding
- Fullness management
- Sticker sending

Usage:
    python3 test_game.py
"""

import sys
import time
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Bottle, User
from game_logic import (
    get_fullness_state, get_emoji_category, validate_emoji_for_color,
    extract_emojis_from_message
)


WEBHOOK_URL = "http://localhost:5000/whatsapp-webhook"
FROM_NUMBER = "33684950535"


def send_webhook_message(message: str, message_id: int) -> bool:
    """Send a test message to the webhook."""
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "test_waba",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": FROM_NUMBER
                                }
                            ],
                            "messages": [
                                {
                                    "from": FROM_NUMBER,
                                    "id": f"wamid.test.{message_id}.{int(time.time())}",
                                    "timestamp": str(int(time.time())),
                                    "type": "text",
                                    "text": {"body": message}
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    try:
        resp = requests.post(
            WEBHOOK_URL,
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def check_bottle_state(session, user_number: str):
    """Check and display current bottle state."""
    user = session.query(User).filter_by(whatsapp_number=user_number).first()
    if not user:
        print("   ⚠️  User not found")
        return None
    
    bottle = session.query(Bottle).filter_by(user_id=user.id).first()
    if not bottle:
        print("   ⚠️  Bottle not found")
        return None
    
    print()
    print("=" * 60)
    print("📊 CURRENT BOTTLE STATE")
    print("=" * 60)
    print(f"   Name: {bottle.name or 'Not set'}")
    print(f"   Game started: {bottle.game_started}")
    print(f"   Fullness level: {bottle.fullness_level:.1f}%")
    print(f"   Fullness state: {get_fullness_state(bottle.fullness_level)}")
    print(f"   Accessory color: {bottle.accessory_color or 'Not set'}")
    print(f"   Current feed count: {bottle.current_feed_count}/3")
    print(f"   Mood: {bottle.mood}")
    if bottle.last_fullness_decrease:
        print(f"   Last decrease: {bottle.last_fullness_decrease}")
    if bottle.last_feed_time:
        print(f"   Last feed: {bottle.last_feed_time}")
    print("=" * 60)
    
    return bottle


def test_emoji_category(emoji_char: str, expected_color: str):
    """Test emoji category lookup."""
    category = get_emoji_category(emoji_char)
    match = category == expected_color
    status = "✅" if match else "❌"
    print(f"   {status} {emoji_char} → {category} (expected: {expected_color})")
    return match


def main():
    """Run game tests."""
    print("=" * 60)
    print("🎮 FEEDING GAME TEST")
    print("=" * 60)
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    # Initialize database
    try:
        init_db()
        session = get_session()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    try:
        # Get or create test user
        from db.db import get_or_create_user, get_or_create_bottle
        user = get_or_create_user(session, FROM_NUMBER)
        bottle = get_or_create_bottle(session, user.id)
        
        print(f"✅ Using user: {user.whatsapp_number}")
        print(f"✅ Using bottle ID: {bottle.id}")
        print()
        
        # Check initial state
        print("1️⃣  CHECKING INITIAL STATE")
        print("-" * 60)
        check_bottle_state(session, FROM_NUMBER)
        print()
        
        # Test emoji category lookup
        print("2️⃣  TESTING EMOJI CATEGORY LOOKUP")
        print("-" * 60)
        print("Testing a few emojis:")
        test_emoji_category("🍷", "GREEN")  # Wine glass - should be GREEN (verre)
        test_emoji_category("📦", "BLUE")   # Package - should be BLUE (papier/carton)
        test_emoji_category("🥤", "YELLOW") # Cup - might be YELLOW (plastique)
        test_emoji_category("❤️", "BLACK")   # Heart - should be BLACK (non-recyclable)
        print()
        
        # Interactive testing
        print("3️⃣  INTERACTIVE GAME TEST")
        print("-" * 60)
        print("You can now test the game by sending messages.")
        print("The Flask server should be running on http://localhost:5000")
        print()
        print("Test steps:")
        print("  1. Send a first message to start the game")
        print("  2. Provide a name when prompted")
        print("  3. Send emojis matching your bottle's accessory color")
        print("  4. Check fullness changes")
        print()
        
        response = input("Do you want to send a test message now? (y/n): ").strip().lower()
        if response == 'y':
            message = input("Enter your test message: ").strip()
            if message:
                print()
                print(f"📤 Sending: \"{message}\"")
                if send_webhook_message(message, 1):
                    print("✅ Message sent successfully")
                    print("   Check your Flask server logs and WhatsApp for response")
                    time.sleep(3)
                    
                    # Check updated state
                    session.refresh(bottle)
                    check_bottle_state(session, FROM_NUMBER)
                else:
                    print("❌ Failed to send message")
        
        print()
        print("4️⃣  MANUAL TESTING INSTRUCTIONS")
        print("-" * 60)
        print("To fully test the game:")
        print()
        print("1. Start your Flask server:")
        print("   python -m endpoint.endpoint")
        print()
        print("2. Send a message to your webhook (first message starts the game)")
        print()
        print("3. Check Flask logs for:")
        print("   - Game initialization")
        print("   - Rules image sent")
        print("   - Name prompt")
        print()
        print("4. Send your name when prompted")
        print()
        print("5. Send emojis matching your bottle's accessory color:")
        bottle = check_bottle_state(session, FROM_NUMBER)
        if bottle and bottle.accessory_color:
            print(f"   Your bottle's color: {bottle.accessory_color}")
            print("   Find matching emojis in emoji_segmentation_corrected.json")
            print("   Send 3 correct emojis to increase fullness by 10%")
        print()
        print("6. Check fullness changes in the database or Flask logs")
        print()
        print("7. Verify stickers are sent (fullness + emotional)")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(main())
