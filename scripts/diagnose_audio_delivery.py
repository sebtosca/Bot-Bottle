#!/usr/bin/env python3
"""Diagnose why audio messages aren't being delivered.

Checks:
1. File format and size
2. URL accessibility
3. WhatsApp API response details
4. Common delivery issues
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote
import requests
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from whatsapp_cloud_client import send_whatsapp_audio, WhatsAppCloudError


def check_file_format(file_path: Path):
    """Check if file meets WhatsApp requirements."""
    print("1️⃣  Checking file format...")
    
    if not file_path.exists():
        print(f"   ❌ File not found: {file_path}")
        return False
    
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ File exists")
    print(f"   ✅ File size: {file_size_mb:.2f} MB")
    
    if file_size_mb > 16:
        print(f"   ❌ File exceeds 16 MB limit!")
        return False
    
    # Check extension
    ext = file_path.suffix.lower()
    supported = ['.mp3', '.ogg', '.m4a', '.aac', '.wav']
    if ext not in supported:
        print(f"   ⚠️  Extension '{ext}' may not be optimal")
        print(f"   Recommended: {', '.join(supported)}")
    else:
        print(f"   ✅ Extension '{ext}' is supported")
    
    return True


def check_url_accessibility(audio_url: str):
    """Check if URL is accessible."""
    print()
    print("2️⃣  Testing URL accessibility...")
    print(f"   URL: {audio_url}")
    
    try:
        # Test with HEAD first
        resp = requests.head(audio_url, timeout=10, allow_redirects=True)
        print(f"   Status: {resp.status_code}")
        
        if resp.status_code == 200:
            content_type = resp.headers.get('Content-Type', 'N/A')
            content_length = resp.headers.get('Content-Length', 'N/A')
            print(f"   ✅ URL is accessible!")
            print(f"   Content-Type: {content_type}")
            print(f"   Content-Length: {content_length} bytes")
            
            if 'audio' not in content_type.lower():
                print(f"   ⚠️  Warning: Content-Type doesn't indicate audio")
            
            # Test with GET to verify full download
            print("   Testing full file download...")
            get_resp = requests.get(audio_url, timeout=30, stream=True)
            if get_resp.status_code == 200:
                # Read first chunk to verify
                chunk = next(get_resp.iter_content(1024), None)
                if chunk:
                    print(f"   ✅ File can be downloaded (first {len(chunk)} bytes received)")
                else:
                    print(f"   ⚠️  File download returned empty")
            else:
                print(f"   ⚠️  GET request returned {get_resp.status_code}")
            
            return True
        else:
            print(f"   ❌ URL returned {resp.status_code}")
            try:
                error_data = resp.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {resp.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to URL")
        print("   Possible causes:")
        print("   - Flask server not running")
        print("   - PUBLIC_BASE_URL is incorrect")
        print("   - Firewall blocking access")
        return False
    except requests.exceptions.Timeout:
        print("   ⚠️  Request timed out")
        print("   URL might be slow or unreachable")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def test_send_with_logging(recipient: str, audio_url: str):
    """Test sending and log full API response."""
    print()
    print("3️⃣  Testing WhatsApp API call...")
    
    try:
        print(f"   Sending to: {recipient}")
        print(f"   Audio URL: {audio_url}")
        print()
        
        message_id = send_whatsapp_audio(
            to_number=recipient,
            media_url=audio_url
        )
        
        print()
        print("   ✅ API call successful!")
        print(f"   Message ID: {message_id}")
        print()
        print("   ⚠️  IMPORTANT: Check Flask server logs to see if WhatsApp")
        print("   is fetching the file. If you don't see a request log, WhatsApp")
        print("   may not be able to access the URL.")
        
        return True, message_id
        
    except WhatsAppCloudError as e:
        print(f"   ❌ API Error: {e}")
        if e.error_code:
            print(f"   Error code: {e.error_code}")
        if e.full_response:
            print(f"   Full response: {json.dumps(e.full_response, indent=2)}")
        return False, None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False, None


def main():
    """Main diagnostic function."""
    print("=" * 60)
    print("🔍 AUDIO MESSAGE DELIVERY DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # Get parameters
    if len(sys.argv) > 1:
        recipient = sys.argv[1]
    else:
        recipient = os.environ.get("WHATSAPP_TEST_NUMBER", "+33684950535")
    
    if len(sys.argv) > 2:
        filename = sys.argv[2]
    else:
        filename = "happy-tune-30s-449787_whatsapp.mp3"
    
    # Ensure + prefix
    if not recipient.startswith("+"):
        recipient = f"+{recipient}"
    
    # Check file
    music_dir = project_root / "music"
    file_path = music_dir / filename
    
    if not check_file_format(file_path):
        return 1
    
    # Check PUBLIC_BASE_URL
    print()
    print("2️⃣  Checking PUBLIC_BASE_URL...")
    if not PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL not set!")
        return 1
    
    if "localhost" in PUBLIC_BASE_URL or "127.0.0.1" in PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL contains localhost!")
        print("   WhatsApp servers cannot access localhost URLs")
        return 1
    
    print(f"   ✅ PUBLIC_BASE_URL: {PUBLIC_BASE_URL}")
    
    # Build URL
    encoded_filename = quote(filename, safe='')
    audio_url = f"{PUBLIC_BASE_URL.rstrip('/')}/music/{encoded_filename}"
    
    # Test URL
    if not check_url_accessibility(audio_url):
        return 1
    
    # Test API call
    success, message_id = test_send_with_logging(recipient, audio_url)
    
    print()
    print("=" * 60)
    print("📋 DIAGNOSIS SUMMARY")
    print("=" * 60)
    
    if success:
        print("✅ All checks passed!")
        print()
        print("If message still not received:")
        print("1. Check Flask server logs for WhatsApp file requests")
        print("2. Verify 24-hour messaging window (recipient must message you first)")
        print("3. Wait 30-60 seconds for delivery")
        print("4. Check WhatsApp webhook for status updates")
        print("5. Verify recipient number is in Meta Console allowed list")
    else:
        print("❌ Some checks failed - see details above")
    
    print()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
