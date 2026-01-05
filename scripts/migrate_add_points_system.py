#!/usr/bin/env python3
"""Migration script to add points and rewards system fields to database.

This script adds:
- New fields to User table (points, title, savings, notifications)
- New fields to Bottle table (points, savings, return tracking)
- New ReceiptVerification table

Usage:
    python scripts/migrate_add_points_system.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from db.db import init_db, get_session, engine


def migrate_add_points_system():
    """Add points system fields and tables to database."""
    print("=" * 60)
    print("Migration: Adding Points & Rewards System")
    print("=" * 60)
    
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    session = get_session()
    
    try:
        # Rollback any previous failed transaction
        session.rollback()
        
        # Check if migration already applied
        try:
            result = session.execute(text("SELECT total_points FROM users LIMIT 1"))
            result.fetchone()
            print("⚠️  Migration appears to already be applied (total_points column exists)")
            print("   Checking for missing columns...")
        except Exception:
            # Column doesn't exist, proceed with migration
            pass
        
        print("Step 1: Adding fields to users table...")
        
        # Add User fields (check if column exists first for PostgreSQL compatibility)
        user_alterations = [
            ("total_points", "INTEGER DEFAULT 0 NOT NULL"),
            ("current_title", "VARCHAR"),
            ("total_money_saved", "FLOAT DEFAULT 0.0 NOT NULL"),
            ("total_co2_saved", "FLOAT DEFAULT 0.0 NOT NULL"),
            ("last_notification_sent", "TIMESTAMP"),
        ]
        
        for col_name, col_def in user_alterations:
            try:
                # Rollback any previous errors
                session.rollback()
                
                # Check if column exists
                check_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name=:col_name
                """)
                result = session.execute(check_sql, {"col_name": col_name}).fetchone()
                
                if result:
                    print(f"   ⚠️  Column {col_name} already exists, skipping")
                else:
                    # Column doesn't exist, add it
                    alter_sql = text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                    session.execute(alter_sql)
                    session.commit()  # Commit after each successful addition
                    print(f"   ✅ Added column: {col_name}")
            except Exception as e:
                session.rollback()  # Rollback on error
                # Check if error is because column already exists
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"   ⚠️  Column {col_name} already exists, skipping")
                else:
                    print(f"   ⚠️  Error adding column {col_name}: {e}")
                # Continue with next column
        
        print("   ✅ User table updated\n")
        
        print("Step 2: Adding fields to bottles table...")
        
        # Add Bottle fields (check if column exists first)
        bottle_alterations = [
            ("points_earned", "INTEGER DEFAULT 0 NOT NULL"),
            ("money_saved", "FLOAT DEFAULT 0.0 NOT NULL"),
            ("co2_saved", "FLOAT DEFAULT 0.0 NOT NULL"),
            ("returned", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("return_receipt_url", "VARCHAR"),
            ("return_verified", "BOOLEAN DEFAULT FALSE NOT NULL"),
            ("returned_at", "TIMESTAMP"),
        ]
        
        for col_name, col_def in bottle_alterations:
            try:
                # Rollback any previous errors
                session.rollback()
                
                # Check if column exists
                check_sql = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='bottles' AND column_name=:col_name
                """)
                result = session.execute(check_sql, {"col_name": col_name}).fetchone()
                
                if result:
                    print(f"   ⚠️  Column {col_name} already exists, skipping")
                else:
                    # Column doesn't exist, add it
                    alter_sql = text(f"ALTER TABLE bottles ADD COLUMN {col_name} {col_def}")
                    session.execute(alter_sql)
                    session.commit()  # Commit after each successful addition
                    print(f"   ✅ Added column: {col_name}")
            except Exception as e:
                session.rollback()  # Rollback on error
                # Check if error is because column already exists
                if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                    print(f"   ⚠️  Column {col_name} already exists, skipping")
                else:
                    print(f"   ⚠️  Error adding column {col_name}: {e}")
                # Continue with next column
        
        print("   ✅ Bottle table updated\n")
        
        print("Step 3: Creating receipt_verifications table...")
        
        # Create ReceiptVerification table
        create_receipt_table = """
        CREATE TABLE IF NOT EXISTS receipt_verifications (
            id SERIAL PRIMARY KEY,
            bottle_id INTEGER NOT NULL REFERENCES bottles(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receipt_image_url VARCHAR NOT NULL,
            ocr_text TEXT,
            verification_status VARCHAR DEFAULT 'pending' NOT NULL,
            points_awarded INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            verified_at TIMESTAMP
        )
        """
        
        try:
            session.execute(text(create_receipt_table))
            session.commit()
            print("   ✅ ReceiptVerification table created\n")
        except Exception as e:
            print(f"   ⚠️  Error creating table (may already exist): {e}\n")
        
        # Create indexes
        print("Step 4: Creating indexes...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_receipt_verifications_bottle_id ON receipt_verifications(bottle_id)",
            "CREATE INDEX IF NOT EXISTS idx_receipt_verifications_user_id ON receipt_verifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_receipt_verifications_status ON receipt_verifications(verification_status)",
        ]
        
        for index_sql in indexes:
            try:
                session.execute(text(index_sql))
                print(f"   ✅ Index created")
            except Exception as e:
                print(f"   ⚠️  {index_sql}: {e}")
        
        session.commit()
        print("   ✅ Indexes created\n")
        
        print("Step 5: Backfilling existing data...")
        
        # Set default values for existing users (only if columns exist)
        try:
            # Check if columns exist before updating
            check_cols = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name IN ('total_points', 'total_money_saved', 'total_co2_saved')
            """)
            existing_cols = [row[0] for row in session.execute(check_cols).fetchall()]
            
            if 'total_points' in existing_cols:
                session.execute(text("UPDATE users SET total_points = 0 WHERE total_points IS NULL"))
            if 'total_money_saved' in existing_cols:
                session.execute(text("UPDATE users SET total_money_saved = 0.0 WHERE total_money_saved IS NULL"))
            if 'total_co2_saved' in existing_cols:
                session.execute(text("UPDATE users SET total_co2_saved = 0.0 WHERE total_co2_saved IS NULL"))
            
            session.commit()
            print("   ✅ User defaults backfilled")
        except Exception as e:
            session.rollback()
            print(f"   ⚠️  Error backfilling users: {e}")
        
        # Set default values for existing bottles (only if columns exist)
        try:
            # Check if columns exist before updating
            check_cols = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='bottles' AND column_name IN ('points_earned', 'money_saved', 'co2_saved', 'returned', 'return_verified')
            """)
            existing_cols = [row[0] for row in session.execute(check_cols).fetchall()]
            
            if 'points_earned' in existing_cols:
                session.execute(text("UPDATE bottles SET points_earned = 0 WHERE points_earned IS NULL"))
            if 'money_saved' in existing_cols:
                session.execute(text("UPDATE bottles SET money_saved = 0.0 WHERE money_saved IS NULL"))
            if 'co2_saved' in existing_cols:
                session.execute(text("UPDATE bottles SET co2_saved = 0.0 WHERE co2_saved IS NULL"))
            if 'returned' in existing_cols:
                session.execute(text("UPDATE bottles SET returned = FALSE WHERE returned IS NULL"))
            if 'return_verified' in existing_cols:
                session.execute(text("UPDATE bottles SET return_verified = FALSE WHERE return_verified IS NULL"))
            
            session.commit()
            print("   ✅ Bottle defaults backfilled")
        except Exception as e:
            session.rollback()
            print(f"   ⚠️  Error backfilling bottles: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNew features available:")
        print("  - Points system (User.total_points)")
        print("  - Title levels (User.current_title)")
        print("  - Savings tracking (User.total_money_saved, User.total_co2_saved)")
        print("  - Receipt verification (ReceiptVerification table)")
        print("  - Return tracking (Bottle.returned, Bottle.return_verified)")
        
        return 0
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(migrate_add_points_system())
