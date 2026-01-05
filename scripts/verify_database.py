#!/usr/bin/env python3
"""Verify database structure and data integrity.

This script checks:
1. All required tables exist
2. All required columns exist in each table
3. Data is loaded (stickers, etc.)
4. Migrations have been applied

Usage:
    python scripts/verify_database.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError


def verify_database():
    """Verify database structure and data."""
    print("=" * 60)
    print("Database Verification")
    print("=" * 60)
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in .env file")
        print("   Please set DATABASE_URL in your .env file")
        return 1
    
    try:
        engine = create_engine(DATABASE_URL, echo=False)
        inspector = inspect(engine)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        print()
        
        # Expected tables
        expected_tables = {
            "users": {
                "columns": ["id", "whatsapp_number", "created_at", "last_seen_at"],
                "description": "WhatsApp users"
            },
            "bottles": {
                "columns": [
                    "id", "user_id", "product_id", "type", "name", "mood", 
                    "personality_level", "fullness_level", "accessory_color",
                    "last_fullness_decrease", "game_started", "current_feed_count",
                    "incorrect_feed_count", "last_feed_time", "recovery_required",
                    "created_at", "updated_at"
                ],
                "description": "Bottle characters with game state"
            },
            "interactions": {
                "columns": ["id", "user_id", "bottle_id", "message_type", "from_user", "content", "created_at"],
                "description": "Message interactions"
            },
            "stickers": {
                "columns": ["id", "filename", "character_id", "mood_tags", "description", "media_type", "url", "created_at"],
                "description": "Stickers and GIFs"
            }
        }
        
        # Check tables
        print("📋 Checking Tables...")
        print("-" * 60)
        existing_tables = inspector.get_table_names()
        all_tables_exist = True
        
        for table_name, table_info in expected_tables.items():
            if table_name in existing_tables:
                print(f"  ✅ {table_name} - {table_info['description']}")
            else:
                print(f"  ❌ {table_name} - MISSING!")
                all_tables_exist = False
        
        if not all_tables_exist:
            print()
            print("⚠️  Some tables are missing. Run migrations or initialize database:")
            print("   python -m db.db  # or start Flask server to auto-create tables")
            return 1
        
        print()
        
        # Check columns for each table
        print("📊 Checking Columns...")
        print("-" * 60)
        all_columns_exist = True
        
        for table_name, table_info in expected_tables.items():
            if table_name not in existing_tables:
                continue
                
            existing_columns = [col["name"] for col in inspector.get_columns(table_name)]
            missing_columns = [col for col in table_info["columns"] if col not in existing_columns]
            
            if missing_columns:
                print(f"  ❌ {table_name} - Missing columns: {', '.join(missing_columns)}")
                all_columns_exist = False
            else:
                print(f"  ✅ {table_name} - All {len(table_info['columns'])} columns present")
        
        if not all_columns_exist:
            print()
            print("⚠️  Some columns are missing. Run migration scripts:")
            print("   python scripts/migrate_add_bottle_name.py")
            print("   python scripts/migrate_add_feeding_game_fields.py")
            print("   python scripts/migrate_add_incorrect_feed_count.py")
            print("   python scripts/migrate_add_gif_support.py")
            print("   python scripts/migrate_add_product_id_to_bottles.py")
            print("   python scripts/migrate_add_character_id_to_stickers.py")
            print("   python scripts/migrate_add_recovery_required.py")
            return 1
        
        print()
        
        # Check data
        print("📦 Checking Data...")
        print("-" * 60)
        
        with engine.connect() as conn:
            # Count records
            users_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            bottles_count = conn.execute(text("SELECT COUNT(*) FROM bottles")).scalar()
            interactions_count = conn.execute(text("SELECT COUNT(*) FROM interactions")).scalar()
            stickers_count = conn.execute(text("SELECT COUNT(*) FROM stickers")).scalar()
            
            print(f"  Users: {users_count}")
            print(f"  Bottles: {bottles_count}")
            print(f"  Interactions: {interactions_count}")
            print(f"  Stickers: {stickers_count}")
            
            # Check sticker types
            if stickers_count > 0:
                sticker_types = conn.execute(
                    text("SELECT media_type, COUNT(*) FROM stickers GROUP BY media_type")
                ).fetchall()
                print()
                print("  Sticker breakdown:")
                for media_type, count in sticker_types:
                    print(f"    - {media_type}: {count}")
                
                # Check character IDs
                character_ids = conn.execute(
                    text("SELECT character_id, COUNT(*) FROM stickers GROUP BY character_id")
                ).fetchall()
                if character_ids:
                    print()
                    print("  Character ID breakdown:")
                    for char_id, count in character_ids:
                        char_display = char_id if char_id else "None (universal)"
                        print(f"    - {char_display}: {count}")
            
            # Check feeding game stickers
            feeding_stickers = conn.execute(
                text("""
                    SELECT COUNT(*) FROM stickers 
                    WHERE description LIKE '%Feeding game%' 
                    OR filename LIKE '%bouteille_affamee%'
                """)
            ).scalar()
            
            if feeding_stickers > 0:
                print()
                print(f"  ✅ Feeding game stickers: {feeding_stickers}")
            else:
                print()
                print("  ⚠️  No feeding game stickers found")
                print("     Run: python scripts/load_feeding_stickers.py")
            
            # Check GIFs
            gif_count = conn.execute(
                text("SELECT COUNT(*) FROM stickers WHERE media_type = 'gif'")
            ).scalar()
            
            if gif_count > 0:
                print(f"  ✅ GIFs: {gif_count}")
            else:
                print("  ⚠️  No GIFs found")
                print("     Run: python scripts/load_gifs.py")
        
        print()
        print("=" * 60)
        print("✅ Database verification complete!")
        print("=" * 60)
        
        if all_tables_exist and all_columns_exist:
            print()
            print("All tables and columns are present. Database structure is correct.")
            if stickers_count == 0:
                print()
                print("💡 Tip: Load your stickers and GIFs:")
                print("   python scripts/load_stickers.py")
                print("   python scripts/load_feeding_stickers.py")
                print("   python scripts/load_gifs.py")
            return 0
        else:
            return 1
        
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("Please check:")
        print("  1. Database server is running")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. Database user has proper permissions")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(verify_database())
