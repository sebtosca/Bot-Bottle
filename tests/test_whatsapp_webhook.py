"""Test script to verify WhatsApp Cloud API webhook is working correctly.

This script tests:
1. Webhook verification (GET request)
2. Webhook message handling (POST request with sample Cloud API payload)

Usage:
    python tests/test_whatsapp_webhook.py <server_url>
    
Example:
    python tests/test_whatsapp_webhook.py http://localhost:5000
    python tests/test_whatsapp_webhook.py https://your-ngrok-url.ngrok-free.app
"""

import sys
import json
import requests
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import WHATSAPP_VERIFY_TOKEN


def test_webhook_verification(server_url: str):
    """Test webhook verification (GET request)."""
    print("=" * 60)
    print("Test 1: Webhook Verification (GET)")
    print("=" * 60)
    
    if not WHATSAPP_VERIFY_TOKEN:
        print("❌ WHATSAPP_VERIFY_TOKEN not set in .env")
        print("   This is required for webhook verification")
        return False
    
    url = f"{server_url.rstrip('/')}/whatsapp-webhook"
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "test_challenge_12345"
    }
    
    print(f"URL: {url}")
    print(f"Verify Token: {WHATSAPP_VERIFY_TOKEN[:10]}...")
    print()
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200 and resp.text == "test_challenge_12345":
            print()
            print("✅ Webhook verification test PASSED")
            return True
        else:
            print()
            print("❌ Webhook verification test FAILED")
            print("   Expected: Status 200 with challenge text")
            print(f"   Got: Status {resp.status_code} with '{resp.text}'")
            return False
            
    except Exception as e:
        print()
        print(f"❌ Error during verification test: {e}")
        return False


def test_webhook_message(server_url: str):
    """Test webhook message handling (POST request with sample payload)."""
    print()
    print("=" * 60)
    print("Test 2: Webhook Message Handling (POST)")
    print("=" * 60)
    
    # Sample WhatsApp Cloud API webhook payload
    sample_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551647916",
                                "phone_number_id": "830701680134677"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": "33684950535"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "33684950535",
                                    "id": "wamid.test123",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {
                                        "body": "Hello, this is a test message!"
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    url = f"{server_url.rstrip('/')}/whatsapp-webhook"
    
    print(f"URL: {url}")
    print("Sending sample text message payload...")
    print()
    
    try:
        resp = requests.post(
            url,
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}...")  # Truncate long responses
        
        if resp.status_code == 200:
            print()
            print("✅ Webhook message handling test PASSED")
            print("   Check server logs to see if message was processed")
            return True
        else:
            print()
            print("❌ Webhook message handling test FAILED")
            print(f"   Expected: Status 200, Got: {resp.status_code}")
            return False
            
    except Exception as e:
        print()
        print(f"❌ Error during message test: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_webhook_sticker(server_url: str):
    """Test webhook with sticker message."""
    print()
    print("=" * 60)
    print("Test 3: Webhook Sticker Message Handling")
    print("=" * 60)
    
    sample_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15551647916",
                                "phone_number_id": "830701680134677"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": "33684950535"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "33684950535",
                                    "id": "wamid.sticker123",
                                    "timestamp": "1234567890",
                                    "type": "sticker",
                                    "sticker": {
                                        "mime_type": "image/webp",
                                        "sha256": "test_hash",
                                        "id": "sticker_id_123"
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    url = f"{server_url.rstrip('/')}/whatsapp-webhook"
    
    print(f"URL: {url}")
    print("Sending sample sticker message payload...")
    print()
    
    try:
        resp = requests.post(
            url,
            json=sample_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}...")
        
        if resp.status_code == 200:
            print()
            print("✅ Webhook sticker handling test PASSED")
            return True
        else:
            print()
            print("❌ Webhook sticker handling test FAILED")
            return False
            
    except Exception as e:
        print()
        print(f"❌ Error during sticker test: {e}")
        return False


def main():
    """Run all webhook tests."""
    print()
    print("🧪 WhatsApp Cloud API Webhook Test Script")
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python tests/test_whatsapp_webhook.py <server_url>")
        print()
        print("Examples:")
        print("  python tests/test_whatsapp_webhook.py http://localhost:5000")
        print("  python tests/test_whatsapp_webhook.py https://your-ngrok-url.ngrok-free.app")
        print()
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip("/")
    
    print(f"Testing webhook at: {server_url}")
    print()
    
    results = []
    
    # Test 1: Webhook verification
    results.append(("Webhook Verification", test_webhook_verification(server_url)))
    
    # Test 2: Text message handling
    results.append(("Text Message Handling", test_webhook_message(server_url)))
    
    # Test 3: Sticker message handling
    results.append(("Sticker Message Handling", test_webhook_sticker(server_url)))
    
    # Summary
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✅ All tests passed!")
        print()
        print("Next steps:")
        print("  1. Configure webhook in Meta Developer Console:")
        print(f"     URL: {server_url}/whatsapp-webhook")
        print(f"     Verify Token: {WHATSAPP_VERIFY_TOKEN}")
        print("  2. Subscribe to 'messages' webhook field")
        print("  3. Send a real message from WhatsApp to test")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print()
        print("Common issues:")
        print("  - Server not running (start with: python endpoint/endpoint.py)")
        print("  - WHATSAPP_VERIFY_TOKEN not set in .env")
        print("  - Wrong server URL")
    
    print()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

