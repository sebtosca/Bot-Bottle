#!/usr/bin/env python3
"""Test Flask routes accessibility for stickers and GIFs via Cloudflare Tunnel."""

import sys
import requests
from pathlib import Path
from urllib.parse import quote

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL, DATABASE_URL
from db.db import init_db, get_session, Sticker


def test_route(url: str, description: str, expected_content_type: str = None) -> dict:
    """Test a specific route and return detailed results."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {description}")
    print(f"URL: {url}")
    print("-" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
    }
    
    result = {
        "url": url,
        "description": description,
        "success": False,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "error": None,
        "is_html": False
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["content_type"] = resp.headers.get('Content-Type', 'N/A')
        result["content_length"] = resp.headers.get('Content-Length', 'N/A')
        
        print(f"Status Code: {resp.status_code}")
        print(f"Content-Type: {result['content_type']}")
        print(f"Content-Length: {result['content_length']}")
        
        if resp.status_code == 200:
            # Check if response is HTML (might be tunnel warning page)
            if 'text/html' in result['content_type'].lower():
                result["is_html"] = True
                print("⚠️  Response is HTML (might be tunnel warning page)")
                if len(resp.text) < 1000:
                    print(f"Response preview: {resp.text[:200]}")
            # Check if content type matches expected
            elif expected_content_type:
                if expected_content_type in result['content_type']:
                    result["success"] = True
                    print("✅ Route is accessible with correct Content-Type!")
                else:
                    print(f"⚠️  Content-Type mismatch: expected '{expected_content_type}', got '{result['content_type']}'")
            else:
                result["success"] = True
                print("✅ Route is accessible!")
        else:
            result["error"] = f"HTTP {resp.status_code}"
            print(f"❌ Route returned error: {resp.status_code}")
            if resp.text:
                preview = resp.text[:500]
                print(f"Response preview: {preview}")
                if 'ngrok' in preview.lower() or 'warning' in preview.lower():
                    print("⚠️  This might be a tunnel warning page")
                    result["is_html"] = True
                    
    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
        print("❌ Error: Request timeout")
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection error: {str(e)}"
        print(f"❌ Error: Connection failed - {e}")
    except Exception as e:
        result["error"] = str(e)
        print(f"❌ Error: {e}")
    
    return result


def main():
    """Test Flask routes accessibility."""
    print("=" * 60)
    print("FLASK ROUTES ACCESSIBILITY TEST")
    print("=" * 60)
    
    # Check PUBLIC_BASE_URL
    if not PUBLIC_BASE_URL:
        print("\n❌ PUBLIC_BASE_URL is not set in .env")
        print("   Set it to your Cloudflare Tunnel URL (without /whatsapp-webhook)")
        print("   Example: PUBLIC_BASE_URL=https://abc123.trycloudflare.com")
        return 1
    
    base_url = PUBLIC_BASE_URL.rstrip("/")
    print(f"\n📋 Using PUBLIC_BASE_URL: {base_url}")
    
    # Check if URL contains /whatsapp-webhook (common mistake)
    if "/whatsapp-webhook" in base_url:
        print("\n⚠️  WARNING: PUBLIC_BASE_URL contains '/whatsapp-webhook'")
        print("   This is incorrect! It should be just the base URL.")
        print(f"   Current: {base_url}")
        corrected_url = base_url.replace("/whatsapp-webhook", "")
        print(f"   Should be: {corrected_url}")
        print("\n   Testing both URLs to show the difference...")
        
        # Test with incorrect URL
        test_route(
            f"{base_url}/health",
            "Health check (with /whatsapp-webhook - INCORRECT)",
        )
        
        # Test with corrected URL
        test_route(
            f"{corrected_url}/health",
            "Health check (corrected - WITHOUT /whatsapp-webhook)",
        )
        
        print("\n" + "=" * 60)
        print("Please update your .env file:")
        print(f"PUBLIC_BASE_URL={corrected_url}")
        print("=" * 60)
        base_url = corrected_url
    
    results = []
    
    # Test 1: Health check
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    results.append(test_route(
        f"{base_url}/health",
        "Health check endpoint"
    ))
    
    # Test 2: Get stickers and GIFs from database
    if not DATABASE_URL:
        print("\n⚠️  DATABASE_URL not set - cannot test with real files from database")
        print("   Testing with sample filenames instead...")
        
        # Test with sample filenames
        results.append(test_route(
            f"{base_url}/stickers/happy_cherry.webp",
            "Stickers route (sample file)",
            "image/webp"
        ))
        results.append(test_route(
            f"{base_url}/gifs/Diva Reaction GIF by MOODMAN_whatsapp.mp4",
            "GIFs route (sample file - unencoded)",
            "video/mp4"
        ))
    else:
        try:
            init_db()
            session = get_session()
            
            # Get stickers from database
            stickers = session.query(Sticker).filter(
                Sticker.media_type == "sticker",
                Sticker.filename.isnot(None),
                Sticker.filename != ""
            ).all()
            
            # Get GIFs from database
            gifs = session.query(Sticker).filter(
                Sticker.media_type == "gif",
                Sticker.filename.isnot(None),
                Sticker.filename != ""
            ).all()
            
            print("\n" + "=" * 60)
            print("TEST 2: Stickers Routes")
            print("=" * 60)
            print(f"Found {len(stickers)} sticker(s) in database")
            
            for sticker in stickers:
                # Test with encoded filename
                encoded_filename = quote(sticker.filename, safe='')
                url_encoded = f"{base_url}/stickers/{encoded_filename}"
                results.append(test_route(
                    url_encoded,
                    f"Sticker: {sticker.filename} (encoded)",
                    "image/webp"
                ))
                
                # Also test with unencoded (if different)
                if encoded_filename != sticker.filename:
                    url_unencoded = f"{base_url}/stickers/{sticker.filename}"
                    results.append(test_route(
                        url_unencoded,
                        f"Sticker: {sticker.filename} (unencoded)",
                        "image/webp"
                    ))
            
            print("\n" + "=" * 60)
            print("TEST 3: GIFs Routes")
            print("=" * 60)
            print(f"Found {len(gifs)} GIF(s) in database")
            
            for gif in gifs:
                # Test with encoded filename
                encoded_filename = quote(gif.filename, safe='')
                url_encoded = f"{base_url}/gifs/{encoded_filename}"
                results.append(test_route(
                    url_encoded,
                    f"GIF: {gif.filename} (encoded)",
                    "video/mp4"
                ))
                
                # Also test with unencoded (if different)
                if encoded_filename != gif.filename:
                    url_unencoded = f"{base_url}/gifs/{gif.filename}"
                    results.append(test_route(
                        url_unencoded,
                        f"GIF: {gif.filename} (unencoded)",
                        "video/mp4"
                    ))
            
            session.close()
            
        except Exception as e:
            print(f"\n❌ Error accessing database: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    html_responses = [r for r in results if r.get("is_html")]
    
    print(f"\nTotal tests: {len(results)}")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    if html_responses:
        print(f"⚠️  HTML responses (tunnel warnings?): {len(html_responses)}")
    
    if successful:
        print("\n✅ Successful routes:")
        for r in successful:
            print(f"   - {r['description']}")
            print(f"     URL: {r['url']}")
            print(f"     Content-Type: {r['content_type']}")
    
    if failed:
        print("\n❌ Failed routes:")
        for r in failed:
            print(f"   - {r['description']}")
            print(f"     URL: {r['url']}")
            print(f"     Error: {r.get('error', f"HTTP {r['status_code']}")}")
            if r.get('is_html'):
                print(f"     ⚠️  Got HTML response (might be tunnel warning page)")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if len(failed) == len(results):
        print("\n❌ All routes failed!")
        print("Possible issues:")
        print("  1. Tunnel service (cloudflared) is not running")
        print("  2. Tunnel is not forwarding to port 5000")
        print("  3. Flask server is not running")
        print("  4. PUBLIC_BASE_URL is incorrect")
        return 1
    elif len(failed) > 0:
        print("\n⚠️  Some routes failed")
        print("Check:")
        print("  - Flask server logs for incoming requests")
        print("  - Files exist in stickers/ and GIF/ directories")
        print("  - Filename encoding matches what's in the database")
        if html_responses:
            print("  - Tunnel warning pages might be blocking access")
        return 1
    else:
        print("\n✅ All routes are accessible!")
        print("Your Flask routes are working correctly via the tunnel.")
        return 0


if __name__ == "__main__":
    exit(main())

