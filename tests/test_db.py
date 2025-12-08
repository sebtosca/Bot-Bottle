"""Test script to verify database setup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, User, Bottle, Interaction
from config import DATABASE_URL


def test_database_connection():
    """Test database connection and initialization."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set in .env file")
        print("   Add: DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname")
        return False
    
    print(f"✅ DATABASE_URL is set")
    print(f"   URL: {DATABASE_URL[:30]}...")
    
    try:
        print("\nInitializing database...")
        init_db()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check that DATABASE_URL is correct")
        print("3. Verify database exists and user has permissions")
        return False


def test_create_user():
    """Test creating a user."""
    print("\n" + "=" * 60)
    print("Create User Test")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # Create test user
        test_number = "+33684950535"
        user = session.query(User).filter_by(whatsapp_number=test_number).first()
        
        if user:
            print(f"✅ User already exists: {user.whatsapp_number}")
            print(f"   ID: {user.id}, Created: {user.created_at}")
        else:
            from datetime import datetime
            user = User(
                whatsapp_number=test_number,
                created_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow()
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            print(f"✅ User created: {user.whatsapp_number}")
            print(f"   ID: {user.id}")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_bottle():
    """Test creating a bottle for a user."""
    print("\n" + "=" * 60)
    print("Create Bottle Test")
    print("=" * 60)
    
    try:
        session = get_session()
        
        # Get or create test user
        test_number = "+33684950535"
        user = session.query(User).filter_by(whatsapp_number=test_number).first()
        
        if not user:
            print("❌ User not found. Run create_user test first.")
            session.close()
            return False
        
        # Get or create bottle
        bottle = session.query(Bottle).filter_by(user_id=user.id).first()
        
        if bottle:
            print(f"✅ Bottle already exists for user {user.id}")
            print(f"   Type: {bottle.type}, Mood: {bottle.mood}, Personality: {bottle.personality_level}")
        else:
            from datetime import datetime
            bottle = Bottle(
                user_id=user.id,
                type="maraschino_cherry",
                mood="neutral",
                personality_level=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(bottle)
            session.commit()
            session.refresh(bottle)
            print(f"✅ Bottle created for user {user.id}")
            print(f"   Type: {bottle.type}, Mood: {bottle.mood}")
        
        session.close()
        return True
    except Exception as e:
        print(f"❌ Failed to create bottle: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all database tests."""
    print("\n" + "=" * 60)
    print("Database Setup Test Suite")
    print("=" * 60)
    print("\nTesting database connection and models...\n")
    
    results = []
    results.append(("Database Connection", test_database_connection()))
    
    if results[0][1]:  # If connection works, test CRUD
        results.append(("Create User", test_create_user()))
        results.append(("Create Bottle", test_create_bottle()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Database is ready!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Fix the issues above.")
        return 1


if __name__ == "__main__":
    exit(main())

