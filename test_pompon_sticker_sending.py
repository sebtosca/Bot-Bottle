#!/usr/bin/env python3
"""Test script to verify Pompon sticker sending works end-to-end.

This script tests:
1. Pompon stickers are in database
2. Sticker selection functions work
3. Flask route can serve Pompon stickers
4. URLs are correctly generated
5. Optional: Test actual WhatsApp sending (if credentials available)

Usage:
    python test_pompon_sticker_sending.py
"""

import sys
import requests
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL, PUBLIC_BASE_URL
from db.db import init_db, get_session, Sticker
from state_logic import select_sticker_by_mood
from game_logic import get_emotional_sticker, get_fullness_sticker


def test_database_stickers():
    """Test 1: Verify Pompon stickers in database."""
    print("=" * 60)
    print("Test 1: Database Stickers")
    print("=" * 60)
    
    session = get_session()
    try:
        pompon_stickers = session.query(Sticker).filter_by(character_id="00002").all()
        
        print(f"  Found {len(pompon_stickers)} Pompon stickers in database")
        
        if len(pompon_stickers) == 0:
            print("  ❌ No Pompon stickers found!")
            return False
        
        # Show sample stickers
        print("\n  Sample stickers:")
        for sticker in pompon_stickers[:5]:
            print(f"    - {sticker.filename} ({sticker.media_type})")
            if sticker.mood_tags:
                print(f"      Mood tags: {sticker.mood_tags}")
        
        print("  ✅ Database check passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    finally:
        session.close()


def test_sticker_selection():
    """Test 2: Verify sticker selection functions."""
    print("\n" + "=" * 60)
    print("Test 2: Sticker Selection Functions")
    print("=" * 60)
    
    base_url = PUBLIC_BASE_URL or "http://localhost:5000"
    character_id = "00002"
    
    try:
        session = get_session()
        
        # Test emotional sticker selection
        print("\n  Testing emotional sticker (happy mood)...")
        emotional = get_emotional_sticker("happy", base_url, character_id)
        
        if emotional:
            print(f"    ✅ Found: {emotional.get('filename')}")
            print(f"    URL: {emotional.get('url')}")
        else:
            print("    ❌ No emotional sticker found")
            return False
        
        # Test state_logic selection
        print("\n  Testing select_sticker_by_mood (happy)...")
        selected = select_sticker_by_mood(session, "happy", base_url, character_id)
        
        if selected:
            print(f"    ✅ Found: {selected.get('filename')}")
            print(f"    URL: {selected.get('url')}")
        else:
            print("    ❌ No sticker found via select_sticker_by_mood")
            return False
        
        # Test feeding sticker
        print("\n  Testing feeding sticker (GREEN, full)...")
        feeding = get_fullness_sticker("GREEN", "full", base_url, character_id)
        
        if feeding:
            print(f"    ✅ Found: {feeding.get('filename')}")
            print(f"    URL: {feeding.get('url')}")
        else:
            print("    ⚠️  No feeding sticker found (may be OK if not in game)")
        
        session.close()
        print("\n  ✅ Sticker selection functions work")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_flask_route(base_url: str):
    """Test 3: Verify Flask route can serve Pompon stickers."""
    print("\n" + "=" * 60)
    print("Test 3: Flask Route Serving")
    print("=" * 60)
    
    # Test with a known Pompon sticker
    test_filename = "happy_cider.webp"
    sticker_url = f"{base_url.rstrip('/')}/stickers/{quote(test_filename, safe='')}"
    
    print(f"\n  Testing URL: {sticker_url}")
    
    try:
        response = requests.get(sticker_url, timeout=10)
        
        print(f"  Status code: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"  Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("  ✅ Flask route successfully serves Pompon sticker!")
            return True
        elif response.status_code == 404:
            print("  ❌ 404 Not Found - Flask route cannot find the sticker")
            print("     Make sure Flask server is running and route is updated")
            return False
        else:
            print(f"  ❌ Unexpected status code: {response.status_code}")
            print(f"     Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("  ❌ Connection error - Flask server may not be running")
        print(f"     Make sure Flask is running at: {base_url}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_file_existence():
    """Test 4: Verify sticker files exist on disk."""
    print("\n" + "=" * 60)
    print("Test 4: File Existence Check")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    pompon_dir = project_root / "Pompom_normand_emotional_sticker"
    
    print(f"\n  Checking directory: {pompon_dir}")
    
    if not pompon_dir.exists():
        print(f"  ❌ Directory does not exist: {pompon_dir}")
        return False
    
    # Check for known Pompon stickers
    test_files = [
        "happy_cider.webp",
        "angry_cider.webp",
        "scared_cider.webp",
        "shocked_cider.webp"
    ]
    
    all_exist = True
    for filename in test_files:
        file_path = pompon_dir / filename
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"    {status} {filename}")
        if not exists:
            all_exist = False
    
    if all_exist:
        print("\n  ✅ All Pompon sticker files exist on disk")
        return True
    else:
        print("\n  ❌ Some Pompon sticker files are missing")
        return False


def test_whatsapp_sending():
    """Test 5: Optional - Test actual WhatsApp sending."""
    print("\n" + "=" * 60)
    print("Test 5: WhatsApp Sending (Optional)")
    print("=" * 60)
    
    try:
        from whatsapp_cloud_client import send_whatsapp_sticker
        from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
        
        if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
            print("  ⚠️  WhatsApp credentials not configured - skipping")
            return None
        
        base_url = PUBLIC_BASE_URL or "http://localhost:5000"
        character_id = "00002"
        
        # Get a Pompon sticker
        emotional = get_emotional_sticker("happy", base_url, character_id)
        
        if not emotional:
            print("  ❌ Could not get Pompon sticker for testing")
            return False
        
        sticker_url = emotional.get('url')
        print(f"\n  Testing WhatsApp send with URL: {sticker_url}")
        print("  ⚠️  This will send a real message - uncomment to test")
        
        # Uncomment to actually send:
        # test_number = "33684950535"  # Replace with your test number
        # result = send_whatsapp_sticker(test_number, sticker_url)
        # print(f"  Result: {result}")
        # return result is not None
        
        return None
        
    except ImportError:
        print("  ⚠️  WhatsApp client not available - skipping")
        return None
    except Exception as e:
        print(f"  ⚠️  Error: {e}")
        return None


def main():
    """Run all tests."""
    print("=" * 60)
    print("Pompon Sticker Sending Test Suite")
    print("=" * 60)
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        init_db()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    base_url = PUBLIC_BASE_URL or "http://localhost:5000"
    
    results = []
    
    # Run tests
    results.append(("Database", test_database_stickers()))
    results.append(("File Existence", test_file_existence()))
    results.append(("Sticker Selection", test_sticker_selection()))
    results.append(("Flask Route", test_flask_route(base_url)))
    
    whatsapp_result = test_whatsapp_sending()
    if whatsapp_result is not None:
        results.append(("WhatsApp Sending", whatsapp_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! Pompon stickers are working.")
    else:
        print("❌ Some tests failed. Check the output above.")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
