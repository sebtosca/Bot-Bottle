"""Migration script to add media_type and url columns to stickers table.

This script adds the new columns needed for GIF support:
- media_type: "sticker" or "gif"
- url: URL for GIFs (null for local sticker files)

Usage:
    python scripts/migrate_add_gif_support.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from db.db import Base, create_engine
from sqlalchemy import text


def migrate_database():
    """Add media_type and url columns to stickers table."""
    print("=" * 60)
    print("Database Migration: Add GIF Support")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Check if columns already exist
            if "postgresql" in DATABASE_URL.lower():
                # PostgreSQL
                check_media_type = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='stickers' AND column_name='media_type'
                """)
                check_url = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='stickers' AND column_name='url'
                """)
                
                result_media_type = conn.execute(check_media_type).fetchone()
                result_url = conn.execute(check_url).fetchone()
                
                # Check if filename is nullable
                check_filename_nullable = text("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name='stickers' AND column_name='filename'
                """)
                result_filename = conn.execute(check_filename_nullable).fetchone()
                filename_is_nullable = result_filename and result_filename[0] == 'YES'
                
                if result_media_type and result_url and filename_is_nullable:
                    print("✅ All columns exist and filename is nullable - migration not needed")
                    return 0
                
                # Add columns if they don't exist
                if not result_media_type:
                    print("Adding media_type column...")
                    conn.execute(text("""
                        ALTER TABLE stickers 
                        ADD COLUMN media_type VARCHAR DEFAULT 'sticker' NOT NULL
                    """))
                    conn.commit()
                    print("✅ media_type column added")
                
                if not result_url:
                    print("Adding url column...")
                    conn.execute(text("""
                        ALTER TABLE stickers 
                        ADD COLUMN url VARCHAR
                    """))
                    conn.commit()
                    print("✅ url column added")
                
                # Make filename nullable (GIFs don't have local filenames)
                if not filename_is_nullable:
                    print("Making filename column nullable...")
                    try:
                        conn.execute(text("""
                            ALTER TABLE stickers 
                            ALTER COLUMN filename DROP NOT NULL
                        """))
                        conn.commit()
                        print("✅ filename column is now nullable")
                    except Exception as e:
                        print(f"   ⚠️  Could not make filename nullable: {e}")
                        print("   You may need to manually run:")
                        print("   ALTER TABLE stickers ALTER COLUMN filename DROP NOT NULL;")
                else:
                    print("✅ filename column is already nullable")
                
                # Update existing stickers to have media_type='sticker'
                print("Updating existing stickers...")
                conn.execute(text("""
                    UPDATE stickers 
                    SET media_type = 'sticker' 
                    WHERE media_type IS NULL OR media_type = ''
                """))
                conn.commit()
                print("✅ Existing stickers updated")
                
            elif "sqlite" in DATABASE_URL.lower():
                # SQLite - need to recreate table
                print("⚠️  SQLite detected - migration requires table recreation")
                print("   This will preserve existing data")
                
                # SQLite doesn't support ALTER TABLE ADD COLUMN easily
                # We'll need to recreate the table
                conn.execute(text("""
                    CREATE TABLE stickers_new (
                        id INTEGER PRIMARY KEY,
                        filename VARCHAR,
                        mood_tags VARCHAR,
                        description VARCHAR,
                        media_type VARCHAR DEFAULT 'sticker' NOT NULL,
                        url VARCHAR,
                        created_at DATETIME NOT NULL
                    )
                """))
                
                conn.execute(text("""
                    INSERT INTO stickers_new (id, filename, mood_tags, description, media_type, url, created_at)
                    SELECT id, filename, mood_tags, description, 'sticker', NULL, created_at
                    FROM stickers
                """))
                
                conn.execute(text("DROP TABLE stickers"))
                conn.execute(text("ALTER TABLE stickers_new RENAME TO stickers"))
                conn.commit()
                print("✅ Table recreated with new columns")
                
            else:
                print("⚠️  Unknown database type - attempting generic migration")
                try:
                    conn.execute(text("ALTER TABLE stickers ADD COLUMN media_type VARCHAR DEFAULT 'sticker'"))
                    conn.execute(text("ALTER TABLE stickers ADD COLUMN url VARCHAR"))
                    conn.commit()
                    print("✅ Columns added")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    print("   You may need to manually add the columns:")
                    print("   ALTER TABLE stickers ADD COLUMN media_type VARCHAR DEFAULT 'sticker';")
                    print("   ALTER TABLE stickers ADD COLUMN url VARCHAR;")
                    return 1
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(migrate_database())

