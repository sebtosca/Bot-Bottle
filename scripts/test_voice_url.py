#!/usr/bin/env python3
"""Test the voice URL directly to see what error Flask returns."""

import sys
from pathlib import Path
from urllib.parse import quote
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL

def main():
    """Test the voice URL."""
    mp3_filename = "[Féminine ]Ma ma......ncer_whatsapp.mp3"
    
    # Test different encoding methods
    encoded1 = quote(mp3_filename)  # Default encoding
    encoded2 = quote(mp3_filename, safe='')  # Encode everything including brackets
    
    url1 = f"{PUBLIC_BASE_URL.rstrip('/')}/voice/{encoded1}"
    url2 = f"{PUBLIC_BASE_URL.rstrip('/')}/voice/{encoded2}"
    
    print("=" * 60)
    print("🧪 TESTING VOICE URL")
    print("=" * 60)
    print()
    print(f"Original filename: {mp3_filename}")
    print()
    print(f"Method 1 (default quote):")
    print(f"  Encoded: {encoded1}")
    print(f"  URL: {url1}")
    print()
    print(f"Method 2 (quote with safe=''):")
    print(f"  Encoded: {encoded2}")
    print(f"  URL: {url2}")
    print()
    
    # Test both URLs
    for i, url in enumerate([url1, url2], 1):
        print(f"Testing Method {i}...")
        try:
            resp = requests.get(url, timeout=10)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"  ✅ SUCCESS! Use Method {i}")
                print(f"  Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
                print(f"  Content-Length: {resp.headers.get('Content-Length', 'N/A')} bytes")
                break
            elif resp.status_code == 400:
                print(f"  ❌ 400 Bad Request")
                try:
                    error_data = resp.json()
                    print(f"  Error details: {error_data}")
                except:
                    print(f"  Response text: {resp.text[:200]}")
            elif resp.status_code == 404:
                print(f"  ❌ 404 Not Found")
                try:
                    error_data = resp.json()
                    print(f"  Error details: {error_data}")
                except:
                    print(f"  Response text: {resp.text[:200]}")
            else:
                print(f"  ⚠️  Status {resp.status_code}")
                print(f"  Response: {resp.text[:200]}")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()
    
    return 0

if __name__ == "__main__":
    exit(main())
