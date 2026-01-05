#!/usr/bin/env python3
"""Test script to verify Pompon stickers can be sent.

This script:
1. Checks if Pompon stickers are loaded in the database
2. Tests sticker selection for Pompon (character_id=00002)
3. Sends a test webhook message with product_id=00002 to trigger Pompon sticker sending

Usage:
    python test_pompon_stickers.py
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL, PUBLIC_BASE_URL
from db.db import init_db, get_session, Sticker, User, Bottle
from state_logic import select_sticker_by_mood
from game_logic import get_emotional_sticker, get_fullness_sticker, get_stickers_for_state


def test_pompon_stickers():
    """Test Pompon sticker loading and selection."""
    print("=" * 60)
    print("Pompon Sticker Test")
    print("=" * 60)
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        init_db()
        session = get_session()
        
        # Check Pompon stickers in database
        print("1️⃣  Checking Pompon Stickers in Database")
        print("-" * 60)
        
        pompon_stickers = session.query(Sticker).filter_by(character_id="00002").all()
        pompon_emotional = [s for s in pompon_stickers if s.media_type == "sticker" and "happy" in (s.mood_tags or "").lower()]
        pompon_feeding = [s for s in pompon_stickers if "GREEN" in (s.mood_tags or "") or "YELLOW" in (s.mood_tags or "")]
        
        print(f"  Total Pompon stickers: {len(pompon_stickers)}")
        print(f"  Emotional stickers: {len([s for s in pompon_stickers if s.media_type == 'sticker' and s.mood_tags and 'happy' in s.mood_tags.lower()])}")
        print(f"  Feeding game stickers: {len([s for s in pompon_stickers if 'GREEN' in (s.mood_tags or '') or 'YELLOW' in (s.mood_tags or '')])}")
        
        if len(pompon_stickers) == 0:
            print()
            print("  ❌ No Pompon stickers found!")
            print("     Run these scripts to load Pompon stickers:")
            print("     python scripts/load_pompon_emotional_stickers.py")
            print("     python scripts/load_pompon_feeding_stickers.py")
            return 1
        
        print("  ✅ Pompon stickers are loaded")
        print()
        
        # Test sticker selection
        print("2️⃣  Testing Sticker Selection for Pompon")
        print("-" * 60)
        
        base_url = PUBLIC_BASE_URL or "https://investment-jamie-merge-downtown.trycloudflare.com"
        character_id = "00002"
        
        # Test emotional sticker selection
        print("  Testing emotional sticker selection (mood=happy)...")
        emotional_sticker = select_sticker_by_mood(
            session=session,
            mood="happy",
            base_url=base_url,
            character_id=character_id
        )
        
        if emotional_sticker:
            print(f"  ✅ Found emotional sticker: {emotional_sticker.get('filename', 'N/A')}")
            print(f"     URL: {emotional_sticker.get('url', 'N/A')[:80]}...")
        else:
            print("  ❌ No emotional sticker found for Pompon")
        
        print()
        
        # Test feeding sticker selection
        print("  Testing feeding sticker selection (GREEN, full)...")
        feeding_sticker = get_fullness_sticker(
            accessory_color="GREEN",
            fullness_state="full",
            base_url=base_url,
            character_id=character_id
        )
        
        if feeding_sticker:
            print(f"  ✅ Found feeding sticker: {feeding_sticker.get('filename', 'N/A')}")
            print(f"     URL: {feeding_sticker.get('url', 'N/A')[:80]}...")
        else:
            print("  ❌ No feeding sticker found for Pompon")
        
        print()
        
        # Test get_emotional_sticker function
        print("  Testing get_emotional_sticker() function...")
        emotional_func = get_emotional_sticker(
            mood="happy",
            base_url=base_url,
            character_id=character_id
        )
        
        if emotional_func:
            print(f"  ✅ Found via get_emotional_sticker(): {emotional_func.get('filename', 'N/A')}")
        else:
            print("  ❌ get_emotional_sticker() returned None")
        
        print()
        
        # Test with a bottle
        print("3️⃣  Testing with Bottle Object")
        print("-" * 60)
        
        # Get or create test user and bottle
        from db.db import get_or_create_user, get_or_create_bottle
        test_number = "33684950535"
        user = get_or_create_user(session, test_number)
        bottle = get_or_create_bottle(session, user.id, product_id="00002", bottle_type="pompon_normand")
        
        print(f"  User: {user.whatsapp_number}")
        print(f"  Bottle ID: {bottle.id}")
        print(f"  Product ID: {bottle.product_id}")
        print(f"  Type: {bottle.type}")
        
        # Test get_stickers_for_state
        bottle.accessory_color = "GREEN"
        bottle.fullness_level = 100.0
        bottle.mood = "happy"
        
        stickers = get_stickers_for_state(bottle, base_url)
        
        if stickers.get("fullness"):
            print(f"  ✅ Fullness sticker: {stickers['fullness'].get('filename', 'N/A')}")
        else:
            print("  ❌ No fullness sticker found")
        
        if stickers.get("emotional"):
            print(f"  ✅ Emotional sticker: {stickers['emotional'].get('filename', 'N/A')}")
        else:
            print("  ❌ No emotional sticker found")
        
        print()
        print("=" * 60)
        print("✅ Pompon Sticker Test Complete!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Make sure your Flask server is running:")
        print("     python -m endpoint.endpoint")
        print()
        print("  2. Test sending a webhook message with Pompon:")
        print("     bash test_multi_character_webhook.sh")
        print("     (or send a message with product_id=00002 in context)")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    sys.exit(test_pompon_stickers())
