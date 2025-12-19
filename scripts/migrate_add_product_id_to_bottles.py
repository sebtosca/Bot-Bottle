#!/usr/bin/env python3
"""Migration script to add product_id column to bottles table.

This script adds the product_id column to the bottles table with a default
value of "00001" (Cherry) for existing bottles.

Usage:
    python scripts/migrate_add_product_id_to_bottles.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_add_product_id():
    """Add product_id column to bottles table."""
    print("=" * 60)
    print("Migration: Add product_id to bottles table")
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
                WHERE table_name='bottles' AND column_name='product_id'
            """))
            
            if result.fetchone():
                print("✅ Column 'product_id' already exists in bottles table")
                return 0
            
            # Add column with default value
            print("Adding product_id column...")
            conn.execute(text("""
                ALTER TABLE bottles 
                ADD COLUMN product_id VARCHAR NOT NULL DEFAULT '00001'
            """))
            
            # Create index on (user_id, product_id) for efficient queries
            print("Creating index on (user_id, product_id)...")
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_bottles_user_product 
                    ON bottles(user_id, product_id)
                """))
            except Exception as e:
                print(f"⚠️  Warning: Could not create index (may already exist): {e}")
            
            conn.commit()
            print("✅ Migration completed successfully!")
            print("   - Added product_id column (default: '00001')")
            print("   - Created index on (user_id, product_id)")
            return 0
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(migrate_add_product_id())
