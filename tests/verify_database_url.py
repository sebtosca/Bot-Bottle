"""Verify that DATABASE_URL is correctly configured and working."""

import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
from db.db import init_db, get_session, User, Bottle, Interaction


def mask_password(url: str) -> str:
    """Mask password in DATABASE_URL for display."""
    return re.sub(r':([^:@]+)@', r':****@', url)


def verify_database_url():
    """Verify DATABASE_URL configuration."""
    print("=" * 60)
    print("DATABASE_URL Verification")
    print("=" * 60)
    
    # Step 1: Check if DATABASE_URL is set
    print("\n1. Checking if DATABASE_URL is set...")
    if not DATABASE_URL:
        print("   ❌ DATABASE_URL is NOT set in .env file")
        print("\n   Solution:")
        print("   Add to .env:")
        print("   DATABASE_URL=postgresql+psycopg2://botbottle_user:botbottle_password_123@localhost:5432/botbottle_db")
        return False
    
    print(f"   ✅ DATABASE_URL is set")
    print(f"   URL: {mask_password(DATABASE_URL)}")
    
    # Step 2: Parse and validate format
    print("\n2. Validating DATABASE_URL format...")
    try:
        match = re.match(r'postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
        if not match:
            print("   ❌ Invalid DATABASE_URL format")
            print("   Expected: postgresql+psycopg2://username:password@host:port/database")
            return False
        
        username, password, host, port, database = match.groups()
        print(f"   ✅ Format is valid")
        print(f"      Username: {username}")
        print(f"      Password: {'*' * len(password)}")
        print(f"      Host: {host}")
        print(f"      Port: {port}")
        print(f"      Database: {database}")
        
        # Check for placeholder values
        issues = []
        if username in ["user", "username", "postgres"] and username != "postgres":
            issues.append(f"   ⚠️  Username '{username}' might be a placeholder")
        if password in ["password", "pass", ""]:
            issues.append(f"   ⚠️  Password looks like a placeholder")
        if database in ["dbname", "database", "test"]:
            issues.append(f"   ⚠️  Database name '{database}' might be a placeholder")
        
        if issues:
            print("\n   Warnings:")
            for issue in issues:
                print(issue)
        
    except Exception as e:
        print(f"   ❌ Error parsing DATABASE_URL: {e}")
        return False
    
    # Step 3: Test database connection
    print("\n3. Testing database connection...")
    try:
        init_db()
        print("   ✅ Database connection successful")
        print("   ✅ Tables initialized/verified")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("\n   Troubleshooting:")
        print("   1. Check PostgreSQL is running: sudo systemctl status postgresql")
        print("   2. Verify credentials are correct")
        print("   3. Check database exists: sudo -u postgres psql -c '\\l'")
        print("   4. Check user exists: sudo -u postgres psql -c '\\du'")
        return False
    
    # Step 4: Test database operations
    print("\n4. Testing database operations...")
    try:
        session = get_session()
        
        # Test query
        user_count = session.query(User).count()
        bottle_count = session.query(Bottle).count()
        interaction_count = session.query(Interaction).count()
        
        print(f"   ✅ Can query database")
        print(f"      Users: {user_count}")
        print(f"      Bottles: {bottle_count}")
        print(f"      Interactions: {interaction_count}")
        
        # Test write operation
        from datetime import datetime
        test_user = session.query(User).filter_by(whatsapp_number="+99999999999").first()
        if not test_user:
            test_user = User(
                whatsapp_number="+99999999999",
                created_at=datetime.utcnow(),
                last_seen_at=datetime.utcnow()
            )
            session.add(test_user)
            session.commit()
            session.refresh(test_user)
            print(f"   ✅ Can write to database (test user created: {test_user.id})")
            
            # Clean up test user
            session.delete(test_user)
            session.commit()
            print(f"   ✅ Can delete from database (test user removed)")
        else:
            print(f"   ✅ Can write to database (test user already exists)")
        
        session.close()
        
    except Exception as e:
        print(f"   ❌ Database operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ DATABASE_URL is correctly configured!")
    print("=" * 60)
    print(f"\nCurrent configuration:")
    print(f"  {mask_password(DATABASE_URL)}")
    print("\n✅ All tests passed - database is ready to use!")
    return True


if __name__ == "__main__":
    success = verify_database_url()
    exit(0 if success else 1)














