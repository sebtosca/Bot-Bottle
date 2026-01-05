#!/usr/bin/env python3
"""Quick verification script to check if Pompon stickers are loaded and accessible.

Usage:
    python verify_pompon_stickers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db.db import init_db, get_session, Sticker
from game_logic import get_emotional_sticker, get_fullness_sticker
from characters import get_character_config

def verify_pompon_stickers():
    """Verify Pompon stickers are loaded and can be retrieved."""
    print("=" * 60)
    print("🔍 Verifying Pompon Stickers")
    print("=" * 60)
    print()
    
    try:
        init_db()
        session = get_session()
        
        # Check database
        print("1️⃣  Database Check")
        print("-" * 60)
        pompon_stickers = session.query(Sticker).filter_by(character_id="00002").all()
        
        emotional_stickers = [
            s for s in pompon_stickers 
            if s.media_type == "sticker" 
            and s.mood_tags 
            and any(m in s.mood_tags.lower() for m in ["happy", "angry", "sad", "scared", "shocked"])
        ]
        
        feeding_stickers = [
            s for s in pompon_stickers 
            if any(color in (s.mood_tags or "") for color in ["GREEN", "YELLOW", "BLUE", "BLACK"])
        ]
        
        print(f"  Total Pompon stickers: {len(pompon_stickers)}")
        print(f"  Emotional stickers: {len(emotional_stickers)}")
        print(f"  Feeding game stickers: {len(feeding_stickers)}")
        print()
        
        if len(pompon_stickers) == 0:
            print("  ❌ No Pompon stickers found!")
            print()
            print("  Run these scripts to load stickers:")
            print("    python scripts/load_pompon_emotional_stickers.py")
            print("    python scripts/load_pompon_feeding_stickers.py")
            return 1
        
        # Show sample stickers
        if emotional_stickers:
            print("  Sample emotional stickers:")
            for s in emotional_stickers[:3]:
                print(f"    - {s.filename} (mood: {s.mood_tags})")
        print()
        
        # Check file system
        print("2️⃣  File System Check")
        print("-" * 60)
        project_root = Path(__file__).parent
        char_config = get_character_config("00002")
        
        emotional_dir = project_root / char_config["sticker_dir"]
        feeding_dir = project_root / char_config["feeding_sticker_dir"]
        
        emotional_files = list(emotional_dir.glob("*.webp")) + list(emotional_dir.glob("*.png"))
        feeding_files = list(feeding_dir.glob("*.webp"))
        
        print(f"  Emotional sticker directory: {emotional_dir}")
        print(f"    Files found: {len(emotional_files)}")
        if emotional_files:
            print(f"    Sample: {emotional_files[0].name}")
        
        print(f"  Feeding sticker directory: {feeding_dir}")
        print(f"    Files found: {len(feeding_files)}")
        if feeding_files:
            print(f"    Sample: {feeding_files[0].name}")
        print()
        
        # Test sticker retrieval functions
        print("3️⃣  Sticker Retrieval Functions")
        print("-" * 60)
        base_url = "http://localhost:5000"
        
        # Test emotional sticker
        happy_sticker = get_emotional_sticker("happy", base_url, "00002")
        if happy_sticker:
            print(f"  ✅ get_emotional_sticker('happy'): {happy_sticker.get('filename')}")
        else:
            print("  ❌ get_emotional_sticker('happy'): Not found")
        
        # Test feeding sticker
        feeding_sticker = get_fullness_sticker("GREEN", "full", base_url, "00002")
        if feeding_sticker:
            print(f"  ✅ get_fullness_sticker('GREEN', 'full'): {feeding_sticker.get('filename')}")
        else:
            print("  ❌ get_fullness_sticker('GREEN', 'full'): Not found")
        
        print()
        print("=" * 60)
        print("✅ Verification Complete!")
        print("=" * 60)
        print()
        print("If all checks passed, run the test script:")
        print("  bash test_pompon_stickers_comprehensive.sh")
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
    sys.exit(verify_pompon_stickers())

