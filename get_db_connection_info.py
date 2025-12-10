#!/usr/bin/env python3
"""Extract database connection info for DBeaver."""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    exit(1)

print("=" * 60)
print("Database Connection Information for DBeaver")
print("=" * 60)

# Parse PostgreSQL URL: postgresql+psycopg2://user:pass@host:port/db
match = re.match(r'postgresql\+psycopg2://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', DATABASE_URL)

if match:
    username, password, host, port, database = match.groups()
    
    print("\n📋 Connection Details:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Database: {database}")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    print("\n" + "=" * 60)
    print("DBeaver Connection Steps:")
    print("=" * 60)
    print("\n1. Open DBeaver CE")
    print("2. Click 'New Database Connection' (plug icon) or Database > New Database Connection")
    print("3. Select 'PostgreSQL' from the list")
    print("4. Fill in the connection settings:")
    print(f"   - Host: {host}")
    print(f"   - Port: {port}")
    print(f"   - Database: {database}")
    print(f"   - Username: {username}")
    print(f"   - Password: {password}")
    print("\n5. Click 'Test Connection' to verify")
    print("6. If successful, click 'Finish'")
    print("\n✅ You should now see your database with tables:")
    print("   - users")
    print("   - bottles")
    print("   - interactions")
    print("   - stickers")
else:
    print("❌ Could not parse DATABASE_URL")
    print(f"   Current value: {DATABASE_URL[:50]}...")
    print("\nExpected format: postgresql+psycopg2://username:password@host:port/database")

