#!/usr/bin/env python3
"""Remove PNG stickers and old format GIFs from database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Sticker

def cleanup_old_media():
    """Remove PNG stickers and old format GIFs."""
    print("=" * 60)
    print("Cleaning Up Old Media")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("\n❌ DATABASE_URL is not set")
        return
    
    try:
        # Initialize database
        init_db()
        session = get_session()
        
        # Find PNG stickers
        png_stickers = session.query(Sticker).filter(
            Sticker.media_type == "sticker",
            Sticker.filename.like("%.png")
        ).all()
        
        # Find old format GIFs (those with URLs, not local files)
        old_gifs = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.url.isnot(None),
            Sticker.filename.is_(None)
        ).all()
        
        print(f"\n📊 Items to remove:")
        print(f"  PNG stickers: {len(png_stickers)}")
        print(f"  Old format GIFs: {len(old_gifs)}")
        
        if len(png_stickers) == 0 and len(old_gifs) == 0:
            print("\n✅ No old media to remove!")
            session.close()
            return
        
        print(f"\n{'=' * 60}")
        print("Removing items...")
        print("=" * 60)
        
        # Remove PNG stickers
        if png_stickers:
            print(f"\n🗑️  Removing {len(png_stickers)} PNG sticker(s):")
            for sticker in png_stickers:
                print(f"    - ID {sticker.id}: {sticker.filename} (mood: {sticker.mood_tags})")
                session.delete(sticker)
        
        # Remove old format GIFs
        if old_gifs:
            print(f"\n🗑️  Removing {len(old_gifs)} old format GIF(s):")
            for gif in old_gifs:
                print(f"    - ID {gif.id}: URL={gif.url[:50]}... (mood: {gif.mood_tags})")
                session.delete(gif)
        
        # Commit changes
        session.commit()
        
        print(f"\n{'=' * 60}")
        print("✅ Cleanup completed successfully!")
        print("=" * 60)
        
        # Show remaining media
        remaining_stickers = session.query(Sticker).filter(Sticker.media_type == "sticker").count()
        remaining_gifs = session.query(Sticker).filter(Sticker.media_type == "gif").count()
        
        print(f"\n📊 Remaining media:")
        print(f"  Stickers: {remaining_stickers}")
        print(f"  GIFs: {remaining_gifs}")
        
        session.close()
        
    except Exception as e:
        print(f"\n❌ Error cleaning up database: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()

if __name__ == "__main__":
    cleanup_old_media()

