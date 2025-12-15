"""Migration script to add incorrect_feed_count field to bottles table.

This script adds the incorrect_feed_count column to the bottles table:
- incorrect_feed_count (Integer, default 0)

Usage:
    python scripts/migrate_add_incorrect_feed_count.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_database():
    """Add incorrect_feed_count column to bottles table."""
    print("=" * 60)
    print("Database Migration: Add Incorrect Feed Count Field")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            col_name = "incorrect_feed_count"
            col_def = "INTEGER DEFAULT 0 NOT NULL"
            
            if "postgresql" in DATABASE_URL.lower():
                # PostgreSQL
                check_column = text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='bottles' AND column_name='{col_name}'
                """)
                
                result = conn.execute(check_column).fetchone()
                
                if result:
                    print(f"✅ {col_name} column already exists - migration not needed")
                    return 0
                
                # Add column if it doesn't exist
                print(f"Adding {col_name} column to bottles table...")
                conn.execute(text(f"""
                    ALTER TABLE bottles 
                    ADD COLUMN {col_name} {col_def}
                """))
                conn.commit()
                print(f"✅ {col_name} column added successfully")
                
            elif "sqlite" in DATABASE_URL.lower():
                # SQLite - need to check if column exists
                print("SQLite detected - checking if column exists...")
                
                # Get table info
                table_info = conn.execute(text("PRAGMA table_info(bottles)")).fetchall()
                column_names = [row[1] for row in table_info]
                
                if col_name in column_names:
                    print(f"✅ {col_name} column already exists - migration not needed")
                    return 0
                
                # SQLite supports ALTER TABLE ADD COLUMN
                print(f"Adding {col_name} column to bottles table...")
                # SQLite doesn't support DEFAULT in ALTER TABLE for some types
                # So we'll add without default and update existing rows
                col_type = "INTEGER"
                conn.execute(text(f"""
                    ALTER TABLE bottles 
                    ADD COLUMN {col_name} {col_type}
                """))
                conn.commit()
                
                # Update existing rows with default value
                conn.execute(text(f"UPDATE bottles SET {col_name} = 0 WHERE {col_name} IS NULL"))
                conn.commit()
                print(f"✅ {col_name} column added successfully")
                
            else:
                # Unknown database - try generic approach
                print("⚠️  Unknown database type - attempting generic migration")
                try:
                    conn.execute(text(f"ALTER TABLE bottles ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
                    print(f"✅ {col_name} column added successfully")
                except Exception as e:
                    print(f"❌ Error adding {col_name}: {e}")
                    print(f"   You may need to manually add the column:")
                    print(f"   ALTER TABLE bottles ADD COLUMN {col_name} {col_def};")
                    return 1
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print(f"\nThe {col_name} column has been added to the bottles table.")
        print("Existing bottles will have incorrect_feed_count: 0")
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(migrate_database())
