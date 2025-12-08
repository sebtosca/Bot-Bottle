#!/usr/bin/env python3
"""Test script to send a sticker directly to a phone number."""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from whatsapp_cloud_client import send_whatsapp_sticker
from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID

def test_send_sticker():
    """Test sending a sticker to a phone number."""
    print("=" * 60)
    print("🧪 TESTING STICKER SENDING")
    print("=" * 60)
    print()
    
    # Check credentials
    if not WHATSAPP_ACCESS_TOKEN:
        print("❌ WHATSAPP_ACCESS_TOKEN not set in .env")
        return False
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not set in .env")
        return False
    
    print("✅ Credentials found")
    print(f"   Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print()
    
    # Get recipient number
    recipient = input("Enter recipient phone number (e.g., +33684950535): ").strip()
    if not recipient:
        print("❌ No recipient number provided")
        return False
    
    # Ensure + prefix
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"
    
    print(f"   Recipient: {recipient}")
    print()
    
    # Get base URL (Cloudflare Tunnel, ngrok, or server URL)
    print("Enter the base URL for stickers (your Cloudflare Tunnel URL, ngrok URL, or server URL):")
    print("   Example: https://your-url.trycloudflare.com (Cloudflare Tunnel)")
    print("   Example: https://your-url.ngrok-free.dev (ngrok)")
    # Check if PUBLIC_BASE_URL is set
    env_base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if env_base_url:
        print(f"   Or press Enter to use PUBLIC_BASE_URL: {env_base_url}")
    base_url = input("Base URL: ").strip()
    
    if not base_url:
        # Use environment variable if available
        base_url = env_base_url
        if not base_url:
            print("❌ No base URL provided and PUBLIC_BASE_URL not set")
            return False
        print(f"   Using PUBLIC_BASE_URL: {base_url}")
    
    # Remove trailing slash
    base_url = base_url.rstrip("/")
    
    # List available stickers
    stickers_dir = Path(__file__).parent / "stickers"
    sticker_files = list(stickers_dir.glob("*.webp")) + list(stickers_dir.glob("*.png"))
    
    if not sticker_files:
        print("❌ No sticker files found in stickers/ directory")
        return False
    
    print()
    print("Available stickers:")
    for i, sticker_file in enumerate(sticker_files, 1):
        print(f"   {i}. {sticker_file.name}")
    
    print()
    sticker_choice = input("Enter sticker number to send (or filename): ").strip()
    
    # Find the sticker
    selected_sticker = None
    if sticker_choice.isdigit():
        idx = int(sticker_choice) - 1
        if 0 <= idx < len(sticker_files):
            selected_sticker = sticker_files[idx]
    else:
        # Try to find by name
        for sticker_file in sticker_files:
            if sticker_choice.lower() in sticker_file.name.lower():
                selected_sticker = sticker_file
                break
    
    if not selected_sticker:
        print(f"❌ Sticker not found: {sticker_choice}")
        return False
    
    # Build sticker URL
    sticker_url = f"{base_url}/stickers/{selected_sticker.name}"
    
    print()
    print("=" * 60)
    print("📤 SENDING STICKER")
    print("=" * 60)
    print(f"   To: {recipient}")
    print(f"   Sticker: {selected_sticker.name}")
    print(f"   URL: {sticker_url}")
    print()
    
    try:
        message_id = send_whatsapp_sticker(
            to_number=recipient,
            media_url=sticker_url
        )
        
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"   Message ID: {message_id}")
        print(f"   Sticker sent successfully!")
        print()
        print("   Check your WhatsApp to see if you received the sticker.")
        return True
        
    except Exception as e:
        print("=" * 60)
        print("❌ ERROR")
        print("=" * 60)
        print(f"   Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_send_sticker()
    sys.exit(0 if success else 1)

