#!/usr/bin/env python3
"""Migration script to set character_id for existing stickers.

This script sets character_id="00001" (Cherry) for all existing stickers
that don't have a character_id set. Universal stickers (shared across characters)
can remain as None.

Usage:
    python scripts/migrate_set_existing_character_ids.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_set_existing_character_ids():
    """Set character_id for existing stickers."""
    print("=" * 60)
    print("Migration: Set character_id for existing stickers")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        
        with engine.connect() as conn:
            # Count existing stickers without character_id
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM stickers 
                WHERE character_id IS NULL
            """))
            count = result.scalar()
            
            if count == 0:
                print("✅ All stickers already have character_id set")
                return 0
            
            print(f"Found {count} sticker(s) without character_id")
            print("Setting character_id='00001' (Cherry) for existing stickers...")
            
            # Set character_id for all existing stickers (default to Cherry)
            conn.execute(text("""
                UPDATE stickers 
                SET character_id = '00001' 
                WHERE character_id IS NULL
            """))
            
            conn.commit()
            print(f"✅ Migration completed successfully!")
            print(f"   - Set character_id='00001' for {count} sticker(s)")
            print("   - Note: Universal stickers can be manually set to NULL if needed")
            return 0
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(migrate_set_existing_character_ids())
