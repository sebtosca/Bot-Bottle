"""Test database connection with new credentials."""

import sys
import os
from pathlib import Path

# Set DATABASE_URL before importing config
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://botbottle_user:botbottle_password_123@localhost:5432/botbottle_db'

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, User, Bottle, Interaction


def test_connection():
    """Test database connection and table creation."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        print("\n1. Initializing database...")
        init_db()
        print("   ✅ Database initialized")
        
        print("\n2. Testing session...")
        session = get_session()
        print("   ✅ Session created")
        
        print("\n3. Testing table creation...")
        # Try to query (tables should exist)
        user_count = session.query(User).count()
        bottle_count = session.query(Bottle).count()
        interaction_count = session.query(Interaction).count()
        
        print(f"   ✅ Tables exist")
        print(f"      Users: {user_count}")
        print(f"      Bottles: {bottle_count}")
        print(f"      Interactions: {interaction_count}")
        
        session.close()
        
        print("\n" + "=" * 60)
        print("✅ Database setup complete!")
        print("=" * 60)
        print("\nUpdate your .env file with:")
        print("DATABASE_URL=postgresql+psycopg2://botbottle_user:botbottle_password_123@localhost:5432/botbottle_db")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)

