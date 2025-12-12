#!/usr/bin/env python3
"""Delete all stickers from the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Sticker

def delete_all_stickers():
    """Delete all stickers from the database."""
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set")
        return 1
    
    try:
        init_db()
        session = get_session()
        
        # Count stickers before deletion
        total_count = session.query(Sticker).count()
        sticker_count = session.query(Sticker).filter_by(media_type="sticker").count()
        gif_count = session.query(Sticker).filter_by(media_type="gif").count()
        
        print("=" * 60)
        print("Deleting Stickers from Database")
        print("=" * 60)
        print(f"\nCurrent stickers in database:")
        print(f"  Total: {total_count}")
        print(f"  - Stickers: {sticker_count}")
        print(f"  - GIFs: {gif_count}")
        
        if total_count == 0:
            print("\n✅ No stickers to delete.")
            session.close()
            return 0
        
        # Delete all stickers
        print(f"\n🗑️  Deleting {total_count} sticker(s)...")
        deleted = session.query(Sticker).delete()
        session.commit()
        
        # Verify deletion
        remaining = session.query(Sticker).count()
        
        print("=" * 60)
        print("Deletion Summary")
        print("=" * 60)
        print(f"  Deleted: {deleted}")
        print(f"  Remaining: {remaining}")
        
        if remaining == 0:
            print("\n✅ All stickers deleted successfully!")
        else:
            print(f"\n⚠️  Warning: {remaining} sticker(s) still remain in database")
        
        session.close()
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(delete_all_stickers())
