#!/usr/bin/env python3
"""Script to send a music/audio message (MP3) via WhatsApp.

Usage:
    python scripts/send_music_message.py [recipient_phone_number] [mp3_filename]
    
    If recipient is not provided, uses default from environment or prompts.
    If filename is not provided, uses the default MP3 file.
    
Examples:
    python scripts/send_music_message.py +33684950535
    python scripts/send_music_message.py +33684950535 "happy-tune-30s-449787.mp3"
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from whatsapp_cloud_client import send_whatsapp_audio, WhatsAppCloudError
from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, PUBLIC_BASE_URL


def main():
    """Send a music message to the recipient phone number."""
    # Get recipient from command line or use default
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = os.environ.get("WHATSAPP_TEST_NUMBER", "+33684950535")
    
    # Get filename from command line or use default
    if len(sys.argv) > 2:
        mp3_filename = sys.argv[2]
    else:
        mp3_filename = "happy-tune-30s-449787_whatsapp.mp3"
    
    # Ensure + prefix
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"
    
    print("=" * 60)
    print("🎵 SENDING MUSIC MESSAGE")
    print("=" * 60)
    
    if not WHATSAPP_ACCESS_TOKEN:
        print("❌ WHATSAPP_ACCESS_TOKEN not set in .env")
        return 1
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return 1
    
    if not PUBLIC_BASE_URL:
        print("❌ PUBLIC_BASE_URL not set in environment.")
        print("   Set it to your public HTTPS base URL (e.g. Cloudflare Tunnel URL),")
        print("   so that WhatsApp can fetch media from:")
        print("     PUBLIC_BASE_URL + '/music/<filename>'")
        return 1
    
    # Check if file exists
    music_dir = project_root / "music"
    mp3_path = music_dir / mp3_filename
    
    if not mp3_path.exists():
        print(f"❌ Music file not found: {mp3_path}")
        print(f"   Available files in music/:")
        if music_dir.exists():
            for f in music_dir.glob("*.mp3"):
                print(f"     - {f.name}")
        return 1
    
    # Build public URL (URL-encode the filename)
    # Use quote with safe='' to encode all special characters
    encoded_filename = quote(mp3_filename, safe='')
    audio_url = f"{PUBLIC_BASE_URL.rstrip('/')}/music/{encoded_filename}"
    print(f"   Original filename: {mp3_filename}")
    print(f"   URL-encoded filename: {encoded_filename}")
    
    print(f"   Recipient: {recipient}")
    print(f"   Filename: {mp3_filename}")
    print(f"   File path: {mp3_path}")
    print(f"   File size: {mp3_path.stat().st_size / 1024:.1f} KB")
    print(f"   Public URL: {audio_url}")
    print()
    
    # Test if URL is accessible
    print("🔍 Testing URL accessibility...")
    try:
        import requests
        test_resp = requests.head(audio_url, timeout=5, allow_redirects=True)
        print(f"   URL test status: {test_resp.status_code}")
        if test_resp.status_code == 200:
            print(f"   ✅ URL is accessible!")
        elif test_resp.status_code == 404:
            print(f"   ❌ URL returns 404 - file not found at this URL")
            print(f"   ⚠️  WhatsApp won't be able to fetch the file")
        else:
            print(f"   ⚠️  URL returned status {test_resp.status_code}")
    except Exception as url_error:
        print(f"   ⚠️  Could not test URL: {url_error}")
        print(f"   ⚠️  Make sure PUBLIC_BASE_URL is correct and server is running")
    print()
    
    try:
        print("📤 Sending music message...")
        message_id = send_whatsapp_audio(
            to_number=recipient,
            media_url=audio_url
        )
        
        print()
        print("=" * 60)
        print("✅ API SUCCESS!")
        print("=" * 60)
        print(f"   Message ID: {message_id}")
        print(f"   Music message accepted by WhatsApp API")
        print()
        print("   ⚠️  IMPORTANT NOTES:")
        print("   1. If you don't see Flask server logs, WhatsApp may not be fetching the file")
        print("   2. Check that PUBLIC_BASE_URL is publicly accessible (not localhost)")
        print("   3. Verify the recipient has messaged you within 24 hours (24-hour window)")
        print("   4. Wait 30-60 seconds for delivery")
        print()
        print(f"   Check WhatsApp on {recipient} to see if you received the music message.")
        return 0
        
    except WhatsAppCloudError as e:
        print()
        print("=" * 60)
        print("❌ WHATSAPP API ERROR")
        print("=" * 60)
        print(f"   Error: {e}")
        if e.error_code:
            print(f"   Error code: {e.error_code}")
        if e.full_response:
            print(f"   Full response: {e.full_response}")
        return 1
        
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
