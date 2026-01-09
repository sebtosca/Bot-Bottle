#!/usr/bin/env python3
"""Test script to verify sticker sending flow components."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.db import get_session, init_db, Bottle, User
from core.game.feeding_game import get_stickers_for_state, get_emotional_sticker
from core.state.bottle_state import select_response_type, select_sticker_by_mood
from config import PUBLIC_BASE_URL, DATABASE_URL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection and initialization."""
    print("\n" + "="*60)
    print("1. Testing Database Connection")
    print("="*60)
    try:
        if not DATABASE_URL:
            print("❌ DATABASE_URL not set")
            return False
        print(f"✅ DATABASE_URL is set: {DATABASE_URL[:20]}...")
        
        init_db()
        print("✅ Database initialized successfully")
        
        session = get_session()
        print("✅ Database session created")
        session.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_sticker_retrieval():
    """Test sticker retrieval functions."""
    print("\n" + "="*60)
    print("2. Testing Sticker Retrieval")
    print("="*60)
    try:
        session = get_session()
        
        # Test get_emotional_sticker
        base_url = PUBLIC_BASE_URL or "http://localhost:5000"
        print(f"Using base_url: {base_url}")
        
        # Test for Cherry (00001)
        print("\nTesting get_emotional_sticker for Cherry (happy mood):")
        cherry_sticker = get_emotional_sticker("happy", base_url, character_id="00001")
        if cherry_sticker:
            print(f"✅ Cherry sticker found: {cherry_sticker.get('filename')}")
            print(f"   URL: {cherry_sticker.get('url')}")
        else:
            print("❌ No Cherry sticker found")
        
        # Test for Pompon (00002)
        print("\nTesting get_emotional_sticker for Pompon (happy mood):")
        pompon_sticker = get_emotional_sticker("happy", base_url, character_id="00002")
        if pompon_sticker:
            print(f"✅ Pompon sticker found: {pompon_sticker.get('filename')}")
            print(f"   URL: {pompon_sticker.get('url')}")
        else:
            print("❌ No Pompon sticker found")
        
        # Test select_sticker_by_mood from database
        print("\nTesting select_sticker_by_mood from database (happy mood):")
        db_sticker = select_sticker_by_mood(session, "happy", base_url, character_id="00001")
        if db_sticker:
            print(f"✅ Database sticker found: {db_sticker.get('filename')}")
            print(f"   URL: {db_sticker.get('url')}")
        else:
            print("❌ No database sticker found")
            print("   Note: Stickers may need to be loaded into database")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ Sticker retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_bottle_sticker_retrieval():
    """Test get_stickers_for_state with a sample bottle."""
    print("\n" + "="*60)
    print("3. Testing Bottle Sticker Retrieval")
    print("="*60)
    try:
        session = get_session()
        base_url = PUBLIC_BASE_URL or "http://localhost:5000"
        
        # Try to get a user and bottle
        user = session.query(User).first()
        if not user:
            print("⚠️  No users found in database - creating test user")
            from db.db import get_or_create_user
            user = get_or_create_user(session, "+1234567890", "Test User")
        
        from db.db import get_active_bottle
        bottle = get_active_bottle(session, user.id)
        
        if not bottle:
            print("⚠️  No active bottle found - cannot test get_stickers_for_state")
            print("   This is expected if no game has been started")
            session.close()
            return True
        
        print(f"Testing with bottle:")
        print(f"  - Product ID: {bottle.product_id}")
        print(f"  - Mood: {bottle.mood}")
        print(f"  - Accessory Color: {bottle.accessory_color}")
        print(f"  - Fullness: {bottle.fullness_level}")
        
        stickers = get_stickers_for_state(bottle, base_url)
        
        print(f"\nSticker retrieval results:")
        if stickers.get("emotional"):
            print(f"✅ Emotional sticker found: {stickers['emotional'].get('filename')}")
            print(f"   URL: {stickers['emotional'].get('url')}")
        else:
            print("❌ No emotional sticker found")
        
        if stickers.get("fullness"):
            print(f"✅ Fullness sticker found: {stickers['fullness'].get('filename')}")
        else:
            print("⚠️  No fullness sticker found (this may be normal)")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ Bottle sticker retrieval error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_response_type_selection():
    """Test response type selection logic."""
    print("\n" + "="*60)
    print("4. Testing Response Type Selection")
    print("="*60)
    try:
        session = get_session()
        
        # Try to get a bottle
        user = session.query(User).first()
        if not user:
            print("⚠️  No users found - skipping response type test")
            session.close()
            return True
        
        from db.db import get_active_bottle
        bottle = get_active_bottle(session, user.id)
        
        if not bottle:
            print("⚠️  No active bottle found - skipping response type test")
            session.close()
            return True
        
        # Test with stickers available
        response_type = select_response_type(
            session,
            bottle.id,
            bottle.mood,
            has_sticker=True,
            has_gif=True
        )
        print(f"✅ Response type with stickers available: {response_type}")
        
        # Test without stickers
        response_type_no_sticker = select_response_type(
            session,
            bottle.id,
            bottle.mood,
            has_sticker=False,
            has_gif=True
        )
        print(f"✅ Response type without stickers: {response_type_no_sticker}")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ Response type selection error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_static_file_paths():
    """Test that sticker files exist in expected directories."""
    print("\n" + "="*60)
    print("5. Testing Static File Paths")
    print("="*60)
    try:
        project_root = Path(__file__).parent
        
        # Check for sticker directories
        sticker_dirs = [
            project_root / "stickers",
            project_root / "Pompom_normand_emotional_sticker",
            project_root / "Pompon_normand_feeding_game_logic_stickers",
            project_root / "feeding_game_logic_stickers",
        ]
        
        found_dirs = []
        for sticker_dir in sticker_dirs:
            if sticker_dir.exists():
                found_dirs.append(sticker_dir)
                # Count .webp files
                webp_files = list(sticker_dir.glob("*.webp"))
                print(f"✅ {sticker_dir.name}: {len(webp_files)} .webp files")
            else:
                print(f"⚠️  {sticker_dir.name}: directory not found")
        
        if not found_dirs:
            print("❌ No sticker directories found!")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Static file path error: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("STICKER SENDING FLOW DIAGNOSTICS")
    print("="*60)
    
    results = []
    results.append(("Database Connection", test_database_connection()))
    results.append(("Sticker Retrieval", test_sticker_retrieval()))
    results.append(("Bottle Sticker Retrieval", test_bottle_sticker_retrieval()))
    results.append(("Response Type Selection", test_response_type_selection()))
    results.append(("Static File Paths", test_static_file_paths()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✅ All tests passed!")
    else:
        print("\n⚠️  Some tests failed - check the output above")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
