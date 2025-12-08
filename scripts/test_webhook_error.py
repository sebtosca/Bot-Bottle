"""Test webhook with detailed error reporting."""

import sys
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_webhook_with_error_capture(server_url: str):
    """Test webhook and capture detailed error information."""
    print("=" * 60)
    print("Testing Webhook with Error Capture")
    print("=" * 60)
    print()
    
    # Real WhatsApp Cloud API payload structure
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1385555166283753",
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
                                        "body": "Test message"
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
    print("Sending webhook request...")
    print()
    
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {resp.status_code}")
        print()
        
        try:
            response_data = resp.json()
            print("Response JSON:")
            print(json.dumps(response_data, indent=2))
            
            if resp.status_code == 500:
                print()
                print("=" * 60)
                print("❌ 500 ERROR DETECTED")
                print("=" * 60)
                print(f"Error Type: {response_data.get('type', 'Unknown')}")
                print(f"Error Message: {response_data.get('error', 'No error message')}")
                if 'details' in response_data:
                    print(f"\nDetails:\n{response_data['details']}")
                print()
                print("Check Flask server console for full traceback")
            elif resp.status_code == 200:
                print()
                print("✅ Webhook processed successfully!")
        except json.JSONDecodeError:
            print("Response (not JSON):")
            print(resp.text[:500])
            
    except Exception as e:
        print(f"❌ Request failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_webhook_error.py <server_url>")
        print("Example: python scripts/test_webhook_error.py https://dragonfly-interfilar-magaly.ngrok-free.dev")
        sys.exit(1)
    
    test_webhook_with_error_capture(sys.argv[1])

