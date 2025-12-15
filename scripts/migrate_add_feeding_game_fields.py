"""Migration script to add feeding game fields to bottles table.

This script adds the following columns to the bottles table:
- fullness_level (Float, default 100.0)
- accessory_color (String, nullable)
- last_fullness_decrease (DateTime, nullable)
- game_started (Boolean, default False)
- current_feed_count (Integer, default 0)
- last_feed_time (DateTime, nullable)

Usage:
    python scripts/migrate_add_feeding_game_fields.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, text


def migrate_database():
    """Add feeding game columns to bottles table."""
    print("=" * 60)
    print("Database Migration: Add Feeding Game Fields")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Define columns to add
            columns_to_add = [
                ("fullness_level", "FLOAT DEFAULT 100.0 NOT NULL"),
                ("accessory_color", "VARCHAR"),
                ("last_fullness_decrease", "TIMESTAMP"),
                ("game_started", "BOOLEAN DEFAULT FALSE NOT NULL"),
                ("current_feed_count", "INTEGER DEFAULT 0 NOT NULL"),
                ("last_feed_time", "TIMESTAMP"),
            ]
            
            if "postgresql" in DATABASE_URL.lower():
                # PostgreSQL
                for col_name, col_def in columns_to_add:
                    check_column = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='bottles' AND column_name='{col_name}'
                    """)
                    
                    result = conn.execute(check_column).fetchone()
                    
                    if result:
                        print(f"✅ {col_name} column already exists - skipping")
                        continue
                    
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
                print("SQLite detected - checking columns...")
                
                # Get table info
                table_info = conn.execute(text("PRAGMA table_info(bottles)")).fetchall()
                column_names = [row[1] for row in table_info]
                
                for col_name, col_def in columns_to_add:
                    if col_name in column_names:
                        print(f"✅ {col_name} column already exists - skipping")
                        continue
                    
                    # SQLite supports ALTER TABLE ADD COLUMN
                    print(f"Adding {col_name} column to bottles table...")
                    # SQLite doesn't support DEFAULT in ALTER TABLE for some types
                    # So we'll add without default and update existing rows
                    if "DEFAULT" in col_def:
                        # Extract type without default
                        col_type = col_def.split("DEFAULT")[0].strip()
                        conn.execute(text(f"""
                            ALTER TABLE bottles 
                            ADD COLUMN {col_name} {col_type}
                        """))
                        conn.commit()
                        
                        # Update existing rows with default values
                        if "fullness_level" in col_name:
                            conn.execute(text("UPDATE bottles SET fullness_level = 100.0 WHERE fullness_level IS NULL"))
                        elif "game_started" in col_name:
                            conn.execute(text("UPDATE bottles SET game_started = 0 WHERE game_started IS NULL"))
                        elif "current_feed_count" in col_name:
                            conn.execute(text("UPDATE bottles SET current_feed_count = 0 WHERE current_feed_count IS NULL"))
                        conn.commit()
                    else:
                        conn.execute(text(f"""
                            ALTER TABLE bottles 
                            ADD COLUMN {col_name} {col_def}
                        """))
                        conn.commit()
                    print(f"✅ {col_name} column added successfully")
                
            else:
                # Unknown database - try generic approach
                print("⚠️  Unknown database type - attempting generic migration")
                for col_name, col_def in columns_to_add:
                    try:
                        conn.execute(text(f"ALTER TABLE bottles ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                        print(f"✅ {col_name} column added successfully")
                    except Exception as e:
                        print(f"❌ Error adding {col_name}: {e}")
                        print(f"   You may need to manually add the column:")
                        print(f"   ALTER TABLE bottles ADD COLUMN {col_name} {col_def};")
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nThe feeding game columns have been added to the bottles table.")
        print("Existing bottles will have:")
        print("  - fullness_level: 100.0")
        print("  - game_started: False")
        print("  - current_feed_count: 0")
        print("  - Other fields: NULL")
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(migrate_database())
