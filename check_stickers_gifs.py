#!/usr/bin/env python3
"""Check stickers and GIFs in the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Sticker

def check_stickers_gifs():
    """Check stickers and GIFs in database."""
    print("=" * 60)
    print("Stickers and GIFs Check")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("\n❌ DATABASE_URL is not set")
        return
    
    try:
        # Initialize database
        init_db()
        session = get_session()
        
        # Get all stickers and GIFs
        all_media = session.query(Sticker).all()
        
        total_count = len(all_media)
        sticker_count = len([s for s in all_media if s.media_type == "sticker"])
        gif_count = len([s for s in all_media if s.media_type == "gif"])
        
        print(f"\n📊 Media Statistics:")
        print(f"  Total media items: {total_count}")
        print(f"  Stickers: {sticker_count}")
        print(f"  GIFs: {gif_count}")
        
        print(f"\n{'=' * 60}")
        
        if total_count == 0:
            print("❌ No stickers or GIFs found in database")
        else:
            print(f"✅ Found {total_count} media item(s):\n")
            
            # Group by media type
            stickers = [s for s in all_media if s.media_type == "sticker"]
            gifs = [s for s in all_media if s.media_type == "gif"]
            
            if stickers:
                print("🎨 STICKERS:")
                for sticker in stickers:
                    print(f"  ID: {sticker.id}")
                    print(f"    Filename: {sticker.filename}")
                    print(f"    Mood tags: {sticker.mood_tags}")
                    print(f"    Description: {sticker.description}")
                    print(f"    URL: {sticker.url if sticker.url else 'None (local file)'}")
                    print(f"    Created: {sticker.created_at}")
                    print()
            
            if gifs:
                print("🎬 GIFs:")
                for gif in gifs:
                    print(f"  ID: {gif.id}")
                    print(f"    Filename: {gif.filename}")
                    print(f"    Mood tags: {gif.mood_tags}")
                    print(f"    Description: {gif.description}")
                    print(f"    URL: {gif.url if gif.url else 'None (local file)'}")
                    print(f"    Created: {gif.created_at}")
                    print()
        
        session.close()
        
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_stickers_gifs()

