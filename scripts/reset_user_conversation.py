#!/usr/bin/env python3
"""Reset a user's conversation to test first contact flow.

This script:
1. Resets the bottle name to None
2. Deletes all interactions for the user
3. Allows testing the first contact flow (name request + rules image)

Usage:
    python scripts/reset_user_conversation.py <phone_number>
    Example: python scripts/reset_user_conversation.py +33684950535
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from db.db import init_db, get_session, User, Bottle, Interaction


def reset_user_conversation(phone_number: str):
    """Reset conversation for a user."""
    print("=" * 60)
    print("Reset User Conversation")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return 1
    
    # Ensure phone number has + prefix
    if not phone_number.startswith("+"):
        phone_number = f"+{phone_number}"
    
    print(f"Phone number: {phone_number}")
    print()
    
    try:
        init_db()
        session = get_session()
        
        # Find user
        user = session.query(User).filter_by(whatsapp_number=phone_number).first()
        if not user:
            print(f"❌ User not found: {phone_number}")
            print("   User will be created on first message")
            return 1
        
        print(f"✅ User found: ID={user.id}")
        
        # Find bottle
        bottle = session.query(Bottle).filter_by(user_id=user.id).first()
        if not bottle:
            print(f"⚠️  No bottle found for user")
            return 0
        
        print(f"✅ Bottle found: ID={bottle.id}, name={bottle.name}")
        
        # Count interactions
        interaction_count = session.query(Interaction).filter_by(bottle_id=bottle.id).count()
        print(f"   Interactions: {interaction_count}")
        
        if interaction_count == 0 and bottle.name is None:
            print("✅ User already in first contact state (no interactions, no name)")
            return 0
        
        # Confirm reset
        print()
        print("⚠️  WARNING: This will:")
        print("   - Delete all interactions for this user")
        print("   - Reset bottle name to None")
        print("   - Reset bottle mood to 'neutral'")
        print("   - Reset personality_level to 0")
        print()
        confirm = input("Continue? (yes/no): ").strip().lower()
        
        if confirm != "yes":
            print("❌ Cancelled")
            return 1
        
        # Delete all interactions
        deleted = session.query(Interaction).filter_by(bottle_id=bottle.id).delete()
        print(f"✅ Deleted {deleted} interactions")
        
        # Reset bottle state
        bottle.name = None
        bottle.mood = "neutral"
        bottle.personality_level = 0
        session.add(bottle)
        session.commit()
        
        print(f"✅ Bottle reset:")
        print(f"   - Name: None")
        print(f"   - Mood: neutral")
        print(f"   - Personality level: 0")
        print()
        print("✅ User conversation reset successfully!")
        print("   Next message from this user will trigger first contact flow")
        
        session.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/reset_user_conversation.py <phone_number>")
        print("Example: python scripts/reset_user_conversation.py +33684950535")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    exit_code = reset_user_conversation(phone_number)
    sys.exit(exit_code)


