#!/usr/bin/env python3
"""Simple script to test database connection."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, is_db_initialized, get_session, User

def test_connection():
    """Test database connection."""
    print("=" * 60)
    print("Database Connection Test")
    print("=" * 60)
    
    # Check if DATABASE_URL is set
    if not DATABASE_URL:
        print("\n❌ DATABASE_URL is not set in .env file")
        print("   Please set DATABASE_URL in your .env file")
        return False
    
    print(f"\n✅ DATABASE_URL is configured")
    # Show partial URL (hide password)
    if "@" in DATABASE_URL:
        url_parts = DATABASE_URL.split("@")
        if len(url_parts) == 2:
            print(f"   URL: {url_parts[0].split('://')[0]}://***@{url_parts[1]}")
    else:
        print(f"   URL: {DATABASE_URL[:50]}...")
    
    # Try to initialize database
    print("\n1. Initializing database...")
    try:
        init_db()
        print("   ✅ Database initialized successfully")
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return False
    
    # Test connection using is_db_initialized()
    print("\n2. Testing connection...")
    if is_db_initialized():
        print("   ✅ Database is connected and reachable")
    else:
        print("   ❌ Database is not reachable")
        return False
    
    # Test a simple query
    print("\n3. Testing database query...")
    try:
        session = get_session()
        user_count = session.query(User).count()
        print(f"   ✅ Query successful")
        print(f"   📊 Found {user_count} user(s) in database")
        session.close()
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Database connection test PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)


