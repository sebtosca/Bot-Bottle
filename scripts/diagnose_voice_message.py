#!/usr/bin/env python3
"""Diagnose why voice messages aren't being delivered.

This script checks:
1. URL accessibility
2. File existence
3. PUBLIC_BASE_URL configuration
4. 24-hour messaging window
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


def main():
    """Diagnose voice message delivery issues."""
    print("=" * 60)
    print("🔍 VOICE MESSAGE DELIVERY DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # Get filename
    if len(sys.argv) > 1:
        mp3_filename = sys.argv[1]
    else:
        mp3_filename = "[Féminine ]Ma ma......ncer_whatsapp.mp3"
    
    # Check 1: File exists
    print("1️⃣  Checking file existence...")
    voice_dir = project_root / "voice_messages"
    mp3_path = voice_dir / mp3_filename
    
    if not mp3_path.exists():
        print(f"   ❌ File not found: {mp3_path}")
        return 1
    else:
        file_size_mb = mp3_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ File exists: {mp3_path.name}")
        print(f"   ✅ File size: {file_size_mb:.2f} MB")
        if file_size_mb > 16:
            print(f"   ❌ File exceeds 16 MB limit!")
            return 1
    
    # Check 2: PUBLIC_BASE_URL
    print()
    print("2️⃣  Checking PUBLIC_BASE_URL...")
    if not PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL not set!")
        print("   Set it in your .env file or environment variables")
        return 1
    
    print(f"   ✅ PUBLIC_BASE_URL: {PUBLIC_BASE_URL}")
    
    # Check if it's localhost (won't work for WhatsApp)
    if "localhost" in PUBLIC_BASE_URL or "127.0.0.1" in PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL contains localhost!")
        print("   WhatsApp servers cannot access localhost URLs")
        print("   Use a public tunnel (Cloudflare Tunnel, ngrok, etc.)")
        return 1
    
    # Check 3: URL accessibility
    print()
    print("3️⃣  Testing URL accessibility...")
    encoded_filename = quote(mp3_filename)
    audio_url = f"{PUBLIC_BASE_URL.rstrip('/')}/voice/{encoded_filename}"
    print(f"   URL: {audio_url}")
    
    try:
        # Test with HEAD request first (faster)
        resp = requests.head(audio_url, timeout=10, allow_redirects=True)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            print("   ✅ URL is accessible!")
            content_type = resp.headers.get('Content-Type', 'N/A')
            print(f"   Content-Type: {content_type}")
            if 'audio' not in content_type.lower():
                print(f"   ⚠️  Warning: Content-Type doesn't look like audio")
        elif resp.status_code == 404:
            print("   ❌ URL returns 404 - file not found")
            print("   This means WhatsApp won't be able to fetch the file")
            print()
            print("   Possible causes:")
            print("   - Flask server not running")
            print("   - Filename mismatch (check URL encoding)")
            print("   - Route not registered correctly")
            return 1
        else:
            print(f"   ⚠️  Unexpected status: {resp.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to URL")
        print("   Possible causes:")
        print("   - Flask server not running")
        print("   - PUBLIC_BASE_URL is incorrect")
        print("   - Firewall blocking access")
        return 1
    except requests.exceptions.Timeout:
        print("   ⚠️  Request timed out")
        print("   URL might be slow or unreachable")
    except Exception as e:
        print(f"   ❌ Error testing URL: {e}")
        return 1
    
    # Check 4: WhatsApp credentials
    print()
    print("4️⃣  Checking WhatsApp credentials...")
    if not WHATSAPP_ACCESS_TOKEN:
        print("   ❌ WHATSAPP_ACCESS_TOKEN not set")
        return 1
    else:
        print("   ✅ WHATSAPP_ACCESS_TOKEN is set")
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("   ❌ WHATSAPP_PHONE_NUMBER_ID not set")
        return 1
    else:
        print("   ✅ WHATSAPP_PHONE_NUMBER_ID is set")
    
    # Check 5: 24-hour window reminder
    print()
    print("5️⃣  24-Hour Messaging Window...")
    print("   ⚠️  IMPORTANT: In test mode, recipient must message you FIRST")
    print("   Then you can reply within 24 hours")
    print("   If recipient hasn't messaged you, WhatsApp won't deliver")
    
    print()
    print("=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("If all checks passed but message still not received:")
    print("1. Wait 30-60 seconds (delivery can be delayed)")
    print("2. Verify recipient messaged you within 24 hours")
    print("3. Check WhatsApp webhook logs for status updates")
    print("4. Verify recipient number is in Meta Console allowed list")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())
