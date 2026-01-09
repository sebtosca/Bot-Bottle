#!/usr/bin/env python3
"""Migration script to add missing columns to users table.

This script adds the following columns to the users table if they don't exist:
- total_points (Integer, default=0)
- current_title (String, nullable)
- total_money_saved (Float, default=0.0)
- total_co2_saved (Float, default=0.0)
- last_notification_sent (DateTime, nullable)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import text, inspect, create_engine
from sqlalchemy.orm import sessionmaker
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

def migrate_users_table():
    """Add missing columns to users table."""
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
    
    print("🔍 Checking users table structure...")
    
    with engine.connect() as conn:
        # Check and add columns one by one
        columns_to_add = [
            ("total_points", "INTEGER NOT NULL DEFAULT 0"),
            ("current_title", "VARCHAR"),
            ("total_money_saved", "FLOAT NOT NULL DEFAULT 0.0"),
            ("total_co2_saved", "FLOAT NOT NULL DEFAULT 0.0"),
            ("last_notification_sent", "TIMESTAMP"),
        ]
        
        for column_name, column_def in columns_to_add:
            if column_exists(conn, "users", column_name):
                print(f"✅ Column '{column_name}' already exists")
            else:
                try:
                    print(f"➕ Adding column '{column_name}'...")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"))
                    conn.commit()
                    print(f"✅ Successfully added column '{column_name}'")
                except Exception as e:
                    print(f"❌ Error adding column '{column_name}': {e}")
                    conn.rollback()
                    return False
    
    print("\n✅ Migration completed successfully!")
    return True

if __name__ == "__main__":
    success = migrate_users_table()
    sys.exit(0 if success else 1)

