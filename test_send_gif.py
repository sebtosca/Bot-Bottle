#!/usr/bin/env python3
"""Simple test script to send a GIF to a phone number."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from whatsapp_cloud_client import send_whatsapp_gif
from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from db.db import init_db, get_session, Sticker

def main():
    """Send a GIF to the recipient phone number."""
    # Get recipient from command line or use default
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = "+33684950535"  # Default recipient
    
    # Ensure + prefix
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"
    
    print("=" * 60)
    print("🧪 TESTING GIF SENDING")
    print("=" * 60)
    
    if not WHATSAPP_ACCESS_TOKEN:
        print("❌ WHATSAPP_ACCESS_TOKEN not set in .env")
        return 1
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return 1
    
    # Get GIF from database
    try:
        init_db()
        session = get_session()
        
        # Get first GIF from database that has a filename (local-file-based)
        gif = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.filename.isnot(None),
            Sticker.filename != ""
        ).first()
        
        if not gif:
            print("❌ No GIFs with filename found in database")
            print("   Run: python scripts/load_gifs.py to load GIF metadata")
            print("   Make sure gifs.json references local MP4/GIF files in the GIF/ directory")
            return 1

        public_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
        if not public_base_url:
            print("❌ PUBLIC_BASE_URL not set in environment.")
            print("   Set it to your public HTTPS base URL (e.g. ngrok HTTPS URL),")
            print("   so that WhatsApp can fetch media from:")
            print("     PUBLIC_BASE_URL + '/gifs/<filename>'")
            return 1

        gif_url = f"{public_base_url}/gifs/{gif.filename}"
        gif_description = gif.description or "GIF"
        gif_mood_tags = gif.mood_tags or "N/A"
        
        print(f"   Recipient: {recipient}")
        print(f"   GIF: {gif_description}")
        print(f"   Mood tags: {gif_mood_tags}")
        print(f"   Filename: {gif.filename}")
        print(f"   URL: {gif_url[:60]}...")
        print()
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error loading GIF from database: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    try:
        print("📤 Sending GIF...")
        message_id = send_whatsapp_gif(
            to_number=recipient,
            media_url=gif_url
        )
        
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"   Message ID: {message_id}")
        print(f"   GIF sent successfully!")
        print()
        print(f"   Check WhatsApp on {recipient} to see if you received the GIF.")
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(f"   Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

