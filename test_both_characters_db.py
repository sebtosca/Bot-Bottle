#!/usr/bin/env python3
"""Test script to verify database state after running test scripts.
Shows user stats, points, and character information."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db.db import init_db, get_session
from db.db import User, Bottle
from characters import get_character_config
from points_system import get_user_stats

def main():
    init_db()
    session = get_session()
    
    # Find test user (default number from test scripts)
    test_number = "33684950535"
    user = session.query(User).filter_by(whatsapp_number=test_number).first()
    
    if not user:
        print(f"❌ User {test_number} not found in database")
        print("   Run test scripts first to create the user and characters.")
        return
    
    print("=" * 60)
    print(f"User: {user.whatsapp_number}")
    print(f"Created: {user.created_at}")
    print("=" * 60)
    
    # Get user stats (points system)
    try:
        stats = get_user_stats(session, user.id)
        if stats:
            print(f"\n📊 User Statistics:")
            print(f"  Total Points: {stats['total_points']}")
            print(f"  Current Title: {stats['current_title']}")
            print(f"  Money Saved: €{stats['total_money_saved']:.2f}")
            print(f"  CO2 Saved: {stats['total_co2_saved']:.2f} kg")
            print(f"  Characters: {stats['character_count']} total")
            print(f"    - Active: {stats['active_characters']}")
            print(f"    - Returned: {stats['returned_characters']}")
            
            if stats['characters']:
                print(f"\n  Per Character:")
                for char in stats['characters']:
                    print(f"    • {char['name']}:")
                    print(f"      - Points: {char['points_earned']}")
                    print(f"      - Money: €{char['money_saved']:.2f}")
                    print(f"      - CO2: {char['co2_saved']:.2f} kg")
                    print(f"      - Fullness: {char['fullness']:.1f}%")
    except Exception as e:
        print(f"  ⚠️  Error getting stats: {e}")
        import traceback
        traceback.print_exc()
    
    # Get all bottles for this user
    bottles = session.query(Bottle).filter_by(user_id=user.id).all()
    
    print(f"\n📦 Characters: {len(bottles)}")
    print("-" * 60)
    
    for bottle in bottles:
        char_config = get_character_config(bottle.product_id)
        print(f"\n{char_config['name']} (product_id={bottle.product_id}):")
        print(f"  Type: {bottle.type}")
        print(f"  Name: {bottle.name}")
        print(f"  Mood: {bottle.mood}")
        print(f"  Game Started: {bottle.game_started}")
        print(f"  Points Earned: {bottle.points_earned}")
        print(f"  Money Saved: €{bottle.money_saved:.2f}")
        print(f"  CO2 Saved: {bottle.co2_saved:.2f} kg")
        print(f"  Returned: {bottle.returned}")
        if bottle.game_started:
            print(f"  Fullness: {bottle.fullness_level:.1f}%")
            print(f"  Accessory Color: {bottle.accessory_color}")
            print(f"  Feed Count: {bottle.current_feed_count}/3")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
