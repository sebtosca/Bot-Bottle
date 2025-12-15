#!/usr/bin/env python3
"""Test script to verify communication logic distribution.

This script sends test messages to the webhook and verifies
that the response types are distributed according to the expected
ratio (80% text_sticker, 20% gif_only).

Usage:
    python3 test_communication_logic.py
    
    Enter messages interactively from the terminal.
    Type 'done' or 'exit' to finish.
"""

import sys
import time
import requests
import json
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import DATABASE_URL
from db.db import init_db, get_session, Interaction, Bottle, User


WEBHOOK_URL = "http://localhost:5000/whatsapp-webhook"
FROM_NUMBER = "33684950535"


def send_webhook_message(message: str, message_id: int) -> bool:
    """Send a test message to the webhook.
    
    Returns:
        True if request was successful, False otherwise.
    """
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "test_waba",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": FROM_NUMBER
                                }
                            ],
                            "messages": [
                                {
                                    "from": FROM_NUMBER,
                                    "id": f"wamid.test.{message_id}.{int(time.time())}",
                                    "timestamp": str(int(time.time())),
                                    "type": "text",
                                    "text": {"body": message}
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    try:
        resp = requests.post(
            WEBHOOK_URL,
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"   ❌ Error sending message: {e}")
        return False


def analyze_response_types(session, bottle_id: int, limit: int = 50) -> Dict[str, int]:
    """Analyze recent bot responses to determine response type distribution.
    
    Returns:
        Dictionary with counts: {"text_sticker": count, "gif_only": count}
    """
    from state_logic import get_recent_bot_response_types
    
    recent_types = get_recent_bot_response_types(session, bottle_id, limit=limit)
    
    counts = {
        "text_sticker": 0,
        "gif_only": 0,
        "text_only": 0  # For historical data
    }
    
    for resp_type in recent_types:
        if resp_type in counts:
            counts[resp_type] += 1
    
    return counts


def test_communication_logic_interactive():
    """Test the communication logic with interactive message input."""
    print("=" * 60)
    print("Communication Logic Test - Interactive Mode")
    print("=" * 60)
    print("Enter messages to send (one per line)")
    print("Type 'done' or 'exit' to finish, or press Ctrl+C to cancel")
    print("Expected distribution: 80% text_sticker, 20% gif_only")
    print()
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set - cannot analyze response types")
        print("   This test requires database access to check response distribution")
        return 1
    
    try:
        # Initialize database
        init_db()
        session = get_session()
        
        # Get or create test user and bottle
        from db.db import get_or_create_user, get_or_create_bottle
        user = get_or_create_user(session, FROM_NUMBER)
        bottle = get_or_create_bottle(session, user.id)
        bottle_id = bottle.id
        
        print(f"✅ Using bottle ID: {bottle_id}")
        print()
        
        # Get initial state (to exclude from analysis)
        initial_count = session.query(Interaction).filter_by(
            bottle_id=bottle_id, from_user="false"
        ).count()
        print(f"📊 Initial bot responses in database: {initial_count}")
        print()
        
        # Collect messages from user
        messages = []
        print("=" * 60)
        print("INPUT MESSAGES")
        print("=" * 60)
        print("Enter your messages (press Enter after each message):")
        print()
        
        message_num = 1
        while True:
            try:
                message = input(f"[{message_num}] Message: ").strip()
                
                if not message:
                    print("   ⚠️  Empty message, skipping...")
                    continue
                
                if message.lower() in ['done', 'exit', 'quit', 'q']:
                    break
                
                messages.append(message)
                message_num += 1
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                if messages:
                    print(f"   Collected {len(messages)} message(s). Continue with these? (y/n): ", end="")
                    try:
                        response = input().strip().lower()
                        if response != 'y':
                            print("   Cancelled.")
                            return 0
                    except:
                        return 0
                else:
                    print("   No messages collected. Exiting.")
                    return 0
                break
        
        if not messages:
            print("❌ No messages to send")
            return 1
        
        print()
        print(f"✅ Collected {len(messages)} message(s)")
        print()
        
        # Send messages
        print("=" * 60)
        print("SENDING MESSAGES")
        print("=" * 60)
        successful = 0
        failed = 0
        
        for i, message in enumerate(messages):
            print(f"[{i+1}/{len(messages)}] Sending: \"{message}\"", end=" ... ")
            
            if send_webhook_message(message, i):
                print("✅")
                successful += 1
            else:
                print("❌")
                failed += 1
            
            # Small delay between messages
            if i < len(messages) - 1:
                time.sleep(2)
        
        print()
        print(f"✅ Successful: {successful}/{len(messages)}")
        if failed > 0:
            print(f"❌ Failed: {failed}/{len(messages)}")
        print()
        
        # Wait a bit for all responses to be processed
        print("⏳ Waiting 5 seconds for responses to be processed...")
        time.sleep(5)
        print()
        
        # Analyze response types
        return analyze_and_display_results(session, bottle_id, len(messages))
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'session' in locals():
            session.close()


def analyze_and_display_results(session, bottle_id: int, num_messages: int) -> int:
    """Analyze and display response type distribution results."""
    print("=" * 60)
    print("ANALYZING RESPONSE TYPES")
    print("=" * 60)
    
    # Get new responses (only those sent during this test)
    new_responses = session.query(Interaction).filter_by(
        bottle_id=bottle_id, from_user="false"
    ).order_by(Interaction.created_at.desc()).limit(num_messages * 2).all()
    
    # Filter to only the most recent ones (after our test started)
    recent_responses = new_responses[:num_messages] if len(new_responses) >= num_messages else new_responses
    
    if not recent_responses:
        print("❌ No bot responses found in database")
        print("   Make sure the webhook is processing messages correctly")
        return 1
    
    # Analyze response types
    counts = analyze_response_types(session, bottle_id, limit=len(recent_responses) + 10)
    
    # Filter out text_only for our analysis (only count text_sticker and gif_only)
    text_sticker_count = counts.get("text_sticker", 0)
    gif_only_count = counts.get("gif_only", 0)
    total_relevant = text_sticker_count + gif_only_count
    
    if total_relevant == 0:
        print("❌ No text_sticker or gif_only responses found")
        print("   All responses were text_only or unknown type")
        return 1
    
    # Calculate percentages
    text_sticker_pct = (text_sticker_count / total_relevant) * 100
    gif_only_pct = (gif_only_count / total_relevant) * 100
    
    print(f"📊 Response Type Distribution:")
    print(f"   text_sticker: {text_sticker_count} ({text_sticker_pct:.1f}%)")
    print(f"   gif_only: {gif_only_count} ({gif_only_pct:.1f}%)")
    if counts.get("text_only", 0) > 0:
        print(f"   text_only: {counts['text_only']} (historical)")
    print()
    
    # Check if distribution is close to 80/20
    # Allow 15% deviation (65-95% range for text_sticker, 5-35% for gif_only)
    tolerance = 15
    target_text_sticker = 80
    target_gif_only = 20
    
    text_sticker_deviation = abs(text_sticker_pct - target_text_sticker)
    gif_only_deviation = abs(gif_only_pct - target_gif_only)
    
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    if text_sticker_deviation <= tolerance and gif_only_deviation <= tolerance:
        print("✅ Distribution is within acceptable range (80% ± 15% for text_sticker)")
        print(f"   text_sticker: {text_sticker_pct:.1f}% (target: 80%, deviation: {text_sticker_deviation:.1f}%)")
        print(f"   gif_only: {gif_only_pct:.1f}% (target: 20%, deviation: {gif_only_deviation:.1f}%)")
        result = 0
    else:
        print("⚠️  Distribution deviates from expected 80/20")
        print(f"   text_sticker: {text_sticker_pct:.1f}% (target: 80%, deviation: {text_sticker_deviation:.1f}%)")
        print(f"   gif_only: {gif_only_pct:.1f}% (target: 20%, deviation: {gif_only_deviation:.1f}%)")
        print()
        print("   Note: With small sample sizes, some deviation is normal.")
        print("   For more accurate results, test with 20+ messages.")
        result = 1
    
    print()
    print("=" * 60)
    
    return result




if __name__ == "__main__":
    exit(test_communication_logic_interactive())
