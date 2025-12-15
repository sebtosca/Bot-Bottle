"""Migration script to add name column to bottles table.

This script adds the name column to the bottles table to store
user-given names for bottles.

Usage:
    python scripts/migrate_add_bottle_name.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_database():
    """Add name column to bottles table."""
    print("=" * 60)
    print("Database Migration: Add Bottle Name Column")
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
                    print("✅ name column already exists - migration not needed")
                    return 0
                
                # Add column if it doesn't exist
                print("Adding name column to bottles table...")
                conn.execute(text("""
                    ALTER TABLE bottles 
                    ADD COLUMN name VARCHAR
                """))
                conn.commit()
                print("✅ name column added successfully")
                
            elif "sqlite" in DATABASE_URL.lower():
                # SQLite - need to check if column exists
                print("SQLite detected - checking if column exists...")
                
                # Get table info
                table_info = conn.execute(text("PRAGMA table_info(bottles)")).fetchall()
                column_names = [row[1] for row in table_info]
                
                if "name" in column_names:
                    print("✅ name column already exists - migration not needed")
                    return 0
                
                # SQLite supports ALTER TABLE ADD COLUMN (since version 3.1.3)
                print("Adding name column to bottles table...")
                conn.execute(text("""
                    ALTER TABLE bottles 
                    ADD COLUMN name VARCHAR
                """))
                conn.commit()
                print("✅ name column added successfully")
                
            else:
                # Unknown database - try generic approach
                print("⚠️  Unknown database type - attempting generic migration")
                try:
                    conn.execute(text("ALTER TABLE bottles ADD COLUMN name VARCHAR"))
                    conn.commit()
                    print("✅ name column added successfully")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    print("   You may need to manually add the column:")
                    print("   ALTER TABLE bottles ADD COLUMN name VARCHAR;")
                    return 1
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nThe 'name' column has been added to the bottles table.")
        print("Existing bottles will have NULL for the name field.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(migrate_database())
