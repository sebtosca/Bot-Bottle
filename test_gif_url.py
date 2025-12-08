#!/usr/bin/env python3
"""Test if the GIF URL is accessible from the internet."""

import sys
import requests
from pathlib import Path
from urllib.parse import quote

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.db import init_db, get_session, Sticker

def main():
    """Test GIF URL accessibility."""
    public_base_url = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not public_base_url:
        print("Usage: python test_gif_url.py <PUBLIC_BASE_URL>")
        print("Example: python test_gif_url.py https://abc123.trycloudflare.com")
        print("Example: python test_gif_url.py https://abc123.ngrok-free.app")
        return 1
    
    public_base_url = public_base_url.rstrip("/")
    
    # Get GIF from database
    try:
        init_db()
        session = get_session()
        
        gif = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.filename.isnot(None),
            Sticker.filename != ""
        ).first()
        
        if not gif:
            print("❌ No GIFs with filename found in database")
            return 1
        
        # Build URL with proper encoding
        encoded_filename = quote(gif.filename, safe='')
        gif_url = f"{public_base_url}/gifs/{encoded_filename}"
        
        print("=" * 60)
        print("Testing GIF URL Accessibility")
        print("=" * 60)
        print(f"Filename: {gif.filename}")
        print(f"Encoded filename: {encoded_filename}")
        print(f"Full URL: {gif_url}")
        print()
        
        # Test if URL is accessible
        print("Testing URL accessibility...")
        try:
            # Some tunnel services (like ngrok free tier) may require browser-like headers
            # to bypass warning pages. Cloudflare Tunnel doesn't need this.
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'ngrok-skip-browser-warning': 'true',  # Bypass ngrok warning page (if using ngrok)
            }
            
            # Use HEAD request first (faster, doesn't download the file)
            resp = requests.head(gif_url, headers=headers, timeout=10, allow_redirects=True)
            print(f"HEAD request status: {resp.status_code}")
            
            # Check if we got a tunnel warning page (common with free ngrok)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '')
                if 'text/html' in content_type:
                    # Might be tunnel warning page, try GET to see content
                    print("  ⚠️  Response is HTML (might be tunnel warning page)")
                    resp_get = requests.get(gif_url, headers=headers, timeout=10, allow_redirects=True)
                    if 'ngrok' in resp_get.text.lower() or 'warning' in resp_get.text.lower():
                        print("  ⚠️  Detected tunnel warning page (likely ngrok free tier)")
                        print("  💡 Tip: Some ngrok free versions show warning pages.")
                        print("     Consider using Cloudflare Tunnel instead for media files.")
                        print("     WhatsApp may still be able to access the file.")
            
            if resp.status_code == 200:
                print("✅ URL is accessible!")
                print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
                print(f"Content-Length: {resp.headers.get('Content-Length', 'N/A')} bytes")
                
                # Also test GET request to verify full download works
                print("\nTesting full download...")
                resp_get = requests.get(gif_url, headers=headers, timeout=30, allow_redirects=True)
                if resp_get.status_code == 200:
                    content_type = resp_get.headers.get('Content-Type', '')
                    if 'video/mp4' in content_type or 'image/gif' in content_type:
                        print(f"✅ Full download successful! ({len(resp_get.content)} bytes)")
                        print(f"   Content-Type: {content_type}")
                    else:
                        print(f"⚠️  Unexpected Content-Type: {content_type}")
                        print(f"   Response length: {len(resp_get.content)} bytes")
                        if len(resp_get.content) < 1000:
                            print(f"   Response preview: {resp_get.text[:200]}")
                else:
                    print(f"❌ GET request failed: {resp_get.status_code}")
                    if resp_get.text:
                        print(f"   Response: {resp_get.text[:200]}")
            else:
                print(f"❌ URL returned error: {resp.status_code}")
                # Try GET to see error details
                resp_get = requests.get(gif_url, headers=headers, timeout=10, allow_redirects=True)
                if resp_get.text:
                    print(f"Response: {resp_get.text[:500]}")
                return 1
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error accessing URL: {e}")
            print("\nPossible issues:")
            print("  1. Flask server is not running")
            print("  2. Tunnel service (cloudflared/ngrok) is not running or URL is incorrect")
            print("  3. Firewall blocking access")
            print("  4. Network connectivity issues")
            return 1
        
        session.close()
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

