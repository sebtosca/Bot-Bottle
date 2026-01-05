#!/usr/bin/env python3
"""Verify that the points system is working correctly.

This script checks:
1. Points are being stored in the database
2. Points are awarded for different activities
3. Titles are being updated correctly
4. Stats can be retrieved

Usage:
    python verify_points_system.py [whatsapp_number]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db.db import init_db, get_session, User, Bottle
from points_system import get_user_stats, POINTS_CHARACTER_COLLECTED, POINTS_FEEDING, POINTS_DAILY_ENGAGEMENT, POINTS_BOTTLE_RETURN, TITLE_THRESHOLDS

def verify_points_system(whatsapp_number: str = None):
    """Verify points system is working."""
    print("=" * 60)
    print("🔍 Verifying Points System")
    print("=" * 60)
    print()
    
    try:
        init_db()
        session = get_session()
        
        # Get user(s) to check
        if whatsapp_number:
            users = [session.query(User).filter_by(whatsapp_number=whatsapp_number).first()]
            users = [u for u in users if u]  # Remove None
        else:
            users = session.query(User).all()
        
        if not users:
            print("❌ No users found in database")
            if whatsapp_number:
                print(f"   Searched for: {whatsapp_number}")
            else:
                print("   Run the test script or interact with the bot to create a user first")
            return 1
        
        print(f"Found {len(users)} user(s) to check")
        print()
        
        for user in users:
            print("=" * 60)
            print(f"👤 User: {user.whatsapp_number}")
            print("=" * 60)
            print()
            
            # Get user stats
            stats = get_user_stats(session, user.id)
            
            print("📊 Current Stats:")
            print("-" * 60)
            print(f"  Total Points: {stats.get('total_points', 0)}")
            print(f"  Current Title: {stats.get('current_title', 'Novice')}")
            print(f"  Total Money Saved: €{stats.get('total_money_saved', 0.0):.2f}")
            print(f"  Total CO2 Saved: {stats.get('total_co2_saved', 0.0):.2f} kg")
            print(f"  Total Characters: {stats.get('character_count', 0)}")
            print(f"  Active Characters: {stats.get('active_characters', 0)}")
            print(f"  Returned Characters: {stats.get('returned_characters', 0)}")
            print()
            
            # Check title thresholds
            print("🏆 Title Progress:")
            print("-" * 60)
            current_points = stats.get('total_points', 0)
            current_title = stats.get('current_title', 'Novice')
            
            print(f"  Current: {current_title} ({current_points} points)")
            
            if current_title == "Novice":
                next_threshold = TITLE_THRESHOLDS["Apprentice"]
                points_needed = next_threshold - current_points
                print(f"  Next: Apprentice (need {points_needed} more points)")
            elif current_title == "Apprentice":
                next_threshold = TITLE_THRESHOLDS["Master"]
                points_needed = next_threshold - current_points
                print(f"  Next: Master (need {points_needed} more points)")
            else:
                print(f"  ✅ Maximum title reached!")
            print()
            
            # Check character details
            characters = stats.get('characters', [])
            if characters:
                print("🎭 Character Details:")
                print("-" * 60)
                for char in characters:
                    print(f"  {char['name']} ({char['product_id']}):")
                    print(f"    Points: {char['points_earned']}")
                    print(f"    Money Saved: €{char['money_saved']:.2f}")
                    print(f"    CO2 Saved: {char['co2_saved']:.2f} kg")
                    print(f"    Fullness: {char['fullness']:.1f}%")
                print()
            
            # Check bottles in database
            bottles = session.query(Bottle).filter_by(user_id=user.id).all()
            if bottles:
                print("🍾 Bottle Records:")
                print("-" * 60)
                for bottle in bottles:
                    print(f"  Bottle ID: {bottle.id}")
                    print(f"    Product ID: {bottle.product_id}")
                    print(f"    Type: {bottle.type}")
                    print(f"    Game Started: {bottle.game_started}")
                    print(f"    Points Earned: {bottle.points_earned}")
                    print(f"    Money Saved: €{bottle.money_saved:.2f}")
                    print(f"    CO2 Saved: {bottle.co2_saved:.2f} kg")
                    print(f"    Returned: {bottle.returned}")
                    print()
            
            # Expected points breakdown
            print("💰 Points Breakdown:")
            print("-" * 60)
            print(f"  Character Collection: {POINTS_CHARACTER_COLLECTED} pts per character")
            print(f"  Feeding (3 correct emojis): {POINTS_FEEDING} pts per feed")
            print(f"  Daily Engagement: {POINTS_DAILY_ENGAGEMENT} pts per day")
            print(f"  Bottle Return (verified): {POINTS_BOTTLE_RETURN} pts")
            print(f"  Milestone Bonuses:")
            print(f"    - 2 characters: +50 pts")
            print(f"    - 3 characters: +100 pts")
            print(f"    - 4+ characters: +200 pts")
            print()
            
            # Verify points make sense
            print("✅ Verification:")
            print("-" * 60)
            expected_min = stats.get('character_count', 0) * POINTS_CHARACTER_COLLECTED
            if current_points >= expected_min:
                print(f"  ✅ Points ({current_points}) >= minimum expected ({expected_min})")
            else:
                print(f"  ⚠️  Points ({current_points}) < minimum expected ({expected_min})")
                print(f"     This might indicate points weren't awarded for character collection")
            
            if stats.get('character_count', 0) >= 2:
                expected_with_milestone = expected_min + 50
                if current_points >= expected_with_milestone:
                    print(f"  ✅ Points include milestone bonus for 2+ characters")
                else:
                    print(f"  ⚠️  Points might be missing milestone bonus")
            
            print()
        
        print("=" * 60)
        print("✅ Verification Complete!")
        print("=" * 60)
        print()
        print("How to test points are working:")
        print("  1. Send 'mes statistiques' or 'mes points' to the bot")
        print("  2. Check Flask server logs for '🎯 Points awarded' messages")
        print("  3. Feed a character 3 correct emojis (should award 10 points)")
        print("  4. Collect a new character (should award 100 points)")
        print("  5. Run this script again to see updated points")
        print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    whatsapp_number = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(verify_points_system(whatsapp_number))

