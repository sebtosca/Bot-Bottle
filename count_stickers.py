#!/usr/bin/env python3
"""Count stickers in the database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Sticker

def count_stickers():
    """Count stickers in the database."""
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set")
        return
    
    try:
        init_db()
        session = get_session()
        
        total_count = session.query(Sticker).count()
        sticker_count = session.query(Sticker).filter_by(media_type="sticker").count()
        gif_count = session.query(Sticker).filter_by(media_type="gif").count()
        
        print(f"Total stickers: {total_count}")
        print(f"  - Stickers: {sticker_count}")
        print(f"  - GIFs: {gif_count}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    count_stickers()
