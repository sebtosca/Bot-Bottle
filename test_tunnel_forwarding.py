#!/usr/bin/env python3
"""Diagnostic script to test if tunneling service (Cloudflare Tunnel, ngrok, etc.) is forwarding requests correctly."""

import sys
import requests
from urllib.parse import quote

def test_route(base_url: str, path: str, description: str) -> bool:
    """Test a specific route through the tunnel."""
    url = f"{base_url.rstrip('/')}{path}"
    print(f"\n{'=' * 60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print("-" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        print(f"Status Code: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"Content-Length: {resp.headers.get('Content-Length', 'N/A')}")
        
        if resp.status_code == 200:
            print("✅ Route is accessible!")
            if len(resp.content) < 500:
                print(f"Response preview: {resp.text[:200]}")
            return True
        else:
            print(f"❌ Route returned error: {resp.status_code}")
            if resp.text:
                preview = resp.text[:500]
                print(f"Response preview: {preview}")
                if 'ngrok' in preview.lower() or 'warning' in preview.lower():
                    print("⚠️  This might be a tunnel warning page (ngrok free tier)")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Test tunnel forwarding for multiple routes."""
    if len(sys.argv) < 2:
        print("Usage: python test_tunnel_forwarding.py <TUNNEL_BASE_URL>")
        print("Example: python test_tunnel_forwarding.py https://abc123.trycloudflare.com")
        print("Example: python test_tunnel_forwarding.py https://abc123.ngrok-free.app")
        return 1
    
    base_url = sys.argv[1].rstrip("/")
    
    print("=" * 60)
    print("TUNNEL FORWARDING DIAGNOSTICS")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print("\nThis script tests multiple routes to verify tunnel forwarding.")
    print("Works with Cloudflare Tunnel, ngrok, or other tunneling services.")
    print("If all routes fail, the tunnel might not be running or forwarding correctly.")
    print("If some routes work but /gifs/ doesn't, there's a route-specific issue.")
    
    results = []
    
    # Test 1: Health check (simplest route)
    results.append(("Health Check", test_route(base_url, "/health", "Health check endpoint")))
    
    # Test 2: Stickers route (similar to GIFs route)
    results.append(("Stickers Route", test_route(base_url, "/stickers/test.webp", "Stickers route (will 404 but should reach Flask)")))
    
    # Test 3: GIFs route with a test filename
    test_filename = "Diva Reaction GIF by MOODMAN_whatsapp.mp4"
    encoded_filename = quote(test_filename, safe='')
    results.append(("GIFs Route", test_route(base_url, f"/gifs/{encoded_filename}", "GIFs route with encoded filename")))
    
    # Test 4: GIFs route with unencoded filename (should fail but shows if route is reached)
    results.append(("GIFs Route (unencoded)", test_route(base_url, f"/gifs/{test_filename}", "GIFs route with unencoded filename")))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == 0:
        print("\n❌ All routes failed!")
        print("Possible issues:")
        print("  1. Tunnel service (cloudflared/ngrok) is not running")
        print("  2. Tunnel is not forwarding to port 5000")
        print("  3. Flask server is not running")
        print("  4. Base URL is incorrect")
        return 1
    elif passed < total:
        print("\n⚠️  Some routes failed")
        print("This suggests the tunnel is working but some routes have issues.")
        if not results[2][1]:  # GIFs route failed
            print("\n💡 The /gifs/ route failed. Check:")
            print("  - Flask server logs for incoming requests")
            print("  - File exists in GIF/ directory")
            print("  - Filename encoding matches what's in the database")
        return 1
    else:
        print("\n✅ All routes are accessible!")
        return 0

if __name__ == "__main__":
    exit(main())

