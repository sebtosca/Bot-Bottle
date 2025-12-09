"""Migration script to add name column to bottles table.

This script adds the name column to the bottles table to store
user-given names for bottles.

Usage:
    python scripts/add_bottle_name_field.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from db.db import create_engine
from sqlalchemy import text


def migrate_database():
    """Add name column to bottles table."""
    print("=" * 60)
    print("Database Migration: Add Bottle Name Field")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if column already exists
            if "postgresql" in DATABASE_URL.lower():
                # PostgreSQL
                check_column = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='bottles' AND column_name='name'
                """)
                
                result = conn.execute(check_column).fetchone()
                if result:
                    print("✅ Column 'name' already exists in bottles table")
                    conn.commit()
                    return 0
                
                # Add column
                print("Adding 'name' column to bottles table...")
                add_column = text("""
                    ALTER TABLE bottles 
                    ADD COLUMN name VARCHAR
                """)
                conn.execute(add_column)
                conn.commit()
                print("✅ Successfully added 'name' column to bottles table")
                
            elif "sqlite" in DATABASE_URL.lower():
                # SQLite
                check_column = text("""
                    PRAGMA table_info(bottles)
                """)
                
                columns = conn.execute(check_column).fetchall()
                column_names = [col[1] for col in columns]
                
                if "name" in column_names:
                    print("✅ Column 'name' already exists in bottles table")
                    return 0
                
                # SQLite doesn't support ALTER TABLE ADD COLUMN easily
                # We'll need to recreate the table (more complex migration)
                print("⚠️  SQLite detected. Column addition requires table recreation.")
                print("   For SQLite, it's recommended to recreate the database or")
                print("   use a tool like sqlite3 to add the column manually:")
                print("   ALTER TABLE bottles ADD COLUMN name TEXT;")
                return 1
            else:
                print("⚠️  Unknown database type. Please add the column manually:")
                print("   ALTER TABLE bottles ADD COLUMN name VARCHAR;")
                return 1
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = migrate_database()
    sys.exit(exit_code)

