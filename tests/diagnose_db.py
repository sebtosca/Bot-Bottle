"""Diagnose database connection issues."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_URL
import re


def diagnose_database():
    """Diagnose database connection issues."""
    print("=" * 60)
    print("Database Connection Diagnostic")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("\n❌ DATABASE_URL is not set in .env file")
        print("\nSolution:")
        print("   Add to .env: DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname")
        return
    
    print(f"\n✅ DATABASE_URL is set")
    
    # Parse the URL (safely, without exposing password)
    try:
        # Extract components
        match = re.match(r'postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)
        if match:
            username, password, host, port, database = match.groups()
            
            print(f"\nConnection details:")
            print(f"  Username: {username}")
            print(f"  Password: {'*' * len(password)}")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  Database: {database}")
            
            # Check for common issues
            issues = []
            
            if username == "user" or username == "username":
                issues.append("⚠️  Username looks like a placeholder - use your actual PostgreSQL username")
            
            if password == "password" or len(password) < 3:
                issues.append("⚠️  Password looks incorrect - use your actual PostgreSQL password")
            
            if database == "dbname" or database == "database":
                issues.append("⚠️  Database name looks like a placeholder - use your actual database name")
            
            if issues:
                print("\n⚠️  Potential issues found:")
                for issue in issues:
                    print(f"  {issue}")
            
            print("\n" + "=" * 60)
            print("How to Fix:")
            print("=" * 60)
            print("\n1. Verify PostgreSQL is running:")
            print("   sudo systemctl status postgresql")
            print("\n2. Check what users exist in PostgreSQL:")
            print("   sudo -u postgres psql -c '\\du'")
            print("\n3. Check what databases exist:")
            print("   sudo -u postgres psql -c '\\l'")
            print("\n4. Create a database and user (if needed):")
            print("   sudo -u postgres psql")
            print("   Then run:")
            print("   CREATE USER your_username WITH PASSWORD 'your_password';")
            print("   CREATE DATABASE your_database OWNER your_username;")
            print("   \\q")
            print("\n5. Update .env file with correct credentials:")
            print(f"   DATABASE_URL=postgresql+psycopg2://your_username:your_password@localhost:5432/your_database")
            
        else:
            print("\n❌ DATABASE_URL format is invalid")
            print("   Expected format: postgresql+psycopg2://username:password@host:port/database")
            print(f"   Current value: {DATABASE_URL[:50]}...")
            
    except Exception as e:
        print(f"\n❌ Error parsing DATABASE_URL: {e}")


if __name__ == "__main__":
    diagnose_database()

