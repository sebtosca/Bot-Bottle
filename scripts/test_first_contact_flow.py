#!/usr/bin/env python3
"""Test script to verify first contact flow.

This simulates the webhook calls that WhatsApp would make:
1. First message from user → Bot should ask for name
2. Second message with name → Bot should store name and send rules image

Usage:
    python scripts/test_first_contact_flow.py
"""

import sys
import json
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv

load_dotenv()

# Get base URL from environment or use default Cloudflare tunnel URL
BASE_URL = os.environ.get("BASE_URL", "https://seen-design-cooking-ebooks.trycloudflare.com")

# Test phone number
TEST_PHONE = "+33684950535"


def simulate_whatsapp_webhook(message_content: str, message_id: str = None):
    """Simulate a WhatsApp webhook call."""
    if message_id is None:
        import time
        message_id = f"test_{int(time.time() * 1000)}"
    
    # Use the correct webhook endpoint
    webhook_url = f"{BASE_URL.rstrip('/')}/whatsapp-webhook"
    
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "test_entry",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "1234567890",
                                "phone_number_id": "test_phone_id"
                            },
                            "contacts": [
                                {
                                    "profile": {
                                        "name": "Test User"
                                    },
                                    "wa_id": TEST_PHONE.replace("+", "")
                                }
                            ],
                            "messages": [
                                {
                                    "from": TEST_PHONE.replace("+", ""),
                                    "id": message_id,
                                    "timestamp": str(int(__import__("time").time())),
                                    "text": {
                                        "body": message_content
                                    },
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    
    print(f"\n{'='*60}")
    print(f"📤 Sending webhook: {message_content}")
    print(f"{'='*60}")
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        if response.text:
            print(f"Response: {response.text[:200]}")
        return response
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Test first contact flow."""
    print("=" * 60)
    print("Testing First Contact Flow")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test phone: {TEST_PHONE}")
    print()
    
    # Step 1: First message (should trigger name request)
    print("STEP 1: First message from user")
    print("-" * 60)
    response1 = simulate_whatsapp_webhook("Bonjour !", "test_msg_1")
    
    if response1 and response1.status_code == 200:
        print("✅ First message processed")
    else:
        print("❌ First message failed")
        return 1
    
    # Wait a bit
    import time
    print("\n⏳ Waiting 2 seconds...")
    time.sleep(2)
    
    # Step 2: Second message with name (should trigger rules image)
    print("\nSTEP 2: User provides name")
    print("-" * 60)
    response2 = simulate_whatsapp_webhook("Ma Bouteille", "test_msg_2")
    
    if response2 and response2.status_code == 200:
        print("✅ Second message processed")
    else:
        print("❌ Second message failed")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)
    print("\nCheck your WhatsApp to verify:")
    print("1. Bot asked for a name")
    print("2. Bot sent rules image after you provided the name")
    print("3. Bot sent welcome message with the bottle name")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

