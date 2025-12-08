#!/usr/bin/env python3
"""Simple test script to send a sticker to a phone number."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from whatsapp_cloud_client import send_whatsapp_sticker
from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID

def main():
    """Send a sticker to the recipient phone number."""
    # Get recipient from command line or use default
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = "+33684950535"  # Default recipient
    
    # Get base URL from command line, environment variable, or use default
    if len(sys.argv) > 2:
        base_url = sys.argv[2].rstrip("/")
    else:
        # Try to get from PUBLIC_BASE_URL environment variable (Cloudflare Tunnel or ngrok)
        base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
        if not base_url:
            print("⚠️  PUBLIC_BASE_URL not set in environment.")
            print("   Set it to your public HTTPS base URL (e.g., Cloudflare Tunnel URL):")
            print("     export PUBLIC_BASE_URL='https://your-url.trycloudflare.com'")
            print("   Or pass it as second argument:")
            print("     python test_send_sticker_simple.py +33684950535 https://your-url.trycloudflare.com")
            return 1
    
    # Ensure + prefix
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"
    
    # Select a sticker (prefer WebP)
    stickers_dir = Path(__file__).parent / "stickers"
    webp_stickers = list(stickers_dir.glob("*.webp"))
    png_stickers = list(stickers_dir.glob("*.png"))
    
    # Prefer WebP, fallback to PNG
    if webp_stickers:
        selected_sticker = webp_stickers[0]  # Use first WebP sticker
    elif png_stickers:
        selected_sticker = png_stickers[0]  # Use first PNG sticker
    else:
        print("❌ No sticker files found in stickers/ directory")
        return 1
    
    sticker_url = f"{base_url}/stickers/{selected_sticker.name}"
    
    print("=" * 60)
    print("🧪 TESTING STICKER SENDING")
    print("=" * 60)
    print(f"   Recipient: {recipient}")
    print(f"   Sticker: {selected_sticker.name}")
    print(f"   URL: {sticker_url}")
    print()
    
    if not WHATSAPP_ACCESS_TOKEN:
        print("❌ WHATSAPP_ACCESS_TOKEN not set in .env")
        return 1
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return 1
    
    try:
        print("📤 Sending sticker...")
        message_id = send_whatsapp_sticker(
            to_number=recipient,
            media_url=sticker_url
        )
        
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"   Message ID: {message_id}")
        print(f"   Sticker sent successfully!")
        print()
        print(f"   Check WhatsApp on {recipient} to see if you received the sticker.")
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

