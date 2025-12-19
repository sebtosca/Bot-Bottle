#!/usr/bin/env python3
"""Migration script to add character_id column to stickers table.

This script adds the character_id column to the stickers table as nullable
(universal stickers can have character_id=None).

Usage:
    python scripts/migrate_add_character_id_to_stickers.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_add_character_id():
    """Add character_id column to stickers table."""
    print("=" * 60)
    print("Migration: Add character_id to stickers table")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='stickers' AND column_name='character_id'
            """))
            
            if result.fetchone():
                print("✅ Column 'character_id' already exists in stickers table")
                return 0
            
            # Add column as nullable (universal stickers can be None)
            print("Adding character_id column...")
            conn.execute(text("""
                ALTER TABLE stickers 
                ADD COLUMN character_id VARCHAR
            """))
            
            # Create index on character_id for filtering
            print("Creating index on character_id...")
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_stickers_character_id 
                    ON stickers(character_id)
                """))
            except Exception as e:
                print(f"⚠️  Warning: Could not create index (may already exist): {e}")
            
            conn.commit()
            print("✅ Migration completed successfully!")
            print("   - Added character_id column (nullable)")
            print("   - Created index on character_id")
            return 0
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(migrate_add_character_id())
