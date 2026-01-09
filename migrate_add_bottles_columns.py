#!/usr/bin/env python3
"""Migration script to add missing columns to bottles table.

This script adds the following columns to the bottles table if they don't exist:
- points_earned (Integer, default=0)
- money_saved (Float, default=0.0)
- co2_saved (Float, default=0.0)
- returned (Boolean, default=False)
- return_receipt_url (String, nullable)
- return_verified (Boolean, default=False)
- returned_at (DateTime, nullable)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import text, create_engine
from db.db import init_db
from config import DATABASE_URL

def column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None

def migrate_bottles_table():
    """Add missing columns to bottles table."""
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL is not set")
        return False
    
    # Initialize database connection
    try:
        init_db()
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize database: {e}")
        return False
    
    # Create engine directly if init_db didn't set it
    try:
        from db.db import engine
        if engine is None:
            engine = create_engine(DATABASE_URL, echo=False)
    except:
        engine = create_engine(DATABASE_URL, echo=False)
    
    print("🔍 Checking bottles table structure...")
    
    with engine.connect() as conn:
        # Check and add columns one by one
        columns_to_add = [
            ("points_earned", "INTEGER NOT NULL DEFAULT 0"),
            ("money_saved", "FLOAT NOT NULL DEFAULT 0.0"),
            ("co2_saved", "FLOAT NOT NULL DEFAULT 0.0"),
            ("returned", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("return_receipt_url", "VARCHAR"),
            ("return_verified", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("returned_at", "TIMESTAMP"),
        ]
        
        for column_name, column_def in columns_to_add:
            if column_exists(conn, "bottles", column_name):
                print(f"✅ Column '{column_name}' already exists")
            else:
                try:
                    print(f"➕ Adding column '{column_name}'...")
                    conn.execute(text(f"ALTER TABLE bottles ADD COLUMN {column_name} {column_def}"))
                    conn.commit()
                    print(f"✅ Successfully added column '{column_name}'")
                except Exception as e:
                    print(f"❌ Error adding column '{column_name}': {e}")
                    conn.rollback()
                    return False
    
    print("\n✅ Migration completed successfully!")
    return True

if __name__ == "__main__":
    success = migrate_bottles_table()
    sys.exit(0 if success else 1)

