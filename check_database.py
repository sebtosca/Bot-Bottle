#!/usr/bin/env python3
"""Check if the database is empty."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, User, Bottle, Interaction, Sticker

def check_database():
    """Check database contents."""
    print("=" * 60)
    print("Database Contents Check")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("\n❌ DATABASE_URL is not set")
        return
    
    try:
        # Initialize database
        init_db()
        session = get_session()
        
        # Count records in each table
        user_count = session.query(User).count()
        bottle_count = session.query(Bottle).count()
        interaction_count = session.query(Interaction).count()
        sticker_count = session.query(Sticker).count()
        
        print(f"\n📊 Database Statistics:")
        print(f"  Users: {user_count}")
        print(f"  Bottles: {bottle_count}")
        print(f"  Interactions: {interaction_count}")
        print(f"  Stickers: {sticker_count}")
        
        total_records = user_count + bottle_count + interaction_count + sticker_count
        
        print(f"\n{'=' * 60}")
        if total_records == 0:
            print("✅ Database is EMPTY (no records found)")
        else:
            print(f"✅ Database contains {total_records} total record(s)")
            
            # Show some details if there are records
            if user_count > 0:
                print(f"\n📱 Users:")
                users = session.query(User).limit(5).all()
                for user in users:
                    print(f"  - {user.whatsapp_number} (ID: {user.id}, created: {user.created_at})")
            
            if bottle_count > 0:
                print(f"\n🍒 Bottles:")
                bottles = session.query(Bottle).limit(5).all()
                for bottle in bottles:
                    print(f"  - Type: {bottle.type}, Mood: {bottle.mood}, Personality: {bottle.personality_level} (User ID: {bottle.user_id})")
            
            if interaction_count > 0:
                print(f"\n💬 Recent Interactions (last 5):")
                interactions = session.query(Interaction).order_by(Interaction.created_at.desc()).limit(5).all()
                for interaction in interactions:
                    from_who = "User" if interaction.from_user == "true" else "Bot"
                    print(f"  - {from_who}: {interaction.content[:50]}... (Type: {interaction.message_type})")
        
        session.close()
        
    except Exception as e:
        print(f"\n❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()

