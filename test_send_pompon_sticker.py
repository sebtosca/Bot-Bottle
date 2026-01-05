#!/usr/bin/env python3
"""Quick test to send a Pompon sticker via WhatsApp.

Usage:
    python test_send_pompon_sticker.py [phone_number]
    
Example:
    python test_send_pompon_sticker.py 33684950535
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import PUBLIC_BASE_URL, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from game_logic import get_emotional_sticker
from whatsapp_cloud_client import send_whatsapp_sticker


def main():
    """Send a test Pompon sticker."""
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
    else:
        phone_number = "33684950535"  # Default test number
    
    print("=" * 60)
    print("Sending Pompon Sticker Test")
    print("=" * 60)
    print(f"Phone number: {phone_number}")
    print()
    
    # Check credentials
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WhatsApp credentials not configured!")
        print("   Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID in .env")
        return 1
    
    base_url = PUBLIC_BASE_URL or "http://localhost:5000"
    character_id = "00002"  # Pompon
    
    # Get Pompon happy sticker
    print("Getting Pompon sticker...")
    sticker = get_emotional_sticker("happy", base_url, character_id)
    
    if not sticker:
        print("❌ Could not get Pompon sticker")
        return 1
    
    sticker_url = sticker.get('url')
    print(f"✅ Found sticker: {sticker.get('filename')}")
    print(f"   URL: {sticker_url}")
    print()
    
    # Send via WhatsApp
    print("Sending via WhatsApp...")
    try:
        result = send_whatsapp_sticker(phone_number, sticker_url)
        
        if result:
            print("✅ Sticker sent successfully!")
            print(f"   Message ID: {result}")
            return 0
        else:
            print("❌ Failed to send sticker")
            return 1
            
    except Exception as e:
        print(f"❌ Error sending sticker: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
