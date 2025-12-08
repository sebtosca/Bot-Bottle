"""Test script to simulate a real WhatsApp text message and verify the response.

This script sends a realistic WhatsApp Cloud API webhook payload to test
if the webhook correctly processes messages and sends replies.
"""

import sys
import json
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_text_message_flow(server_url: str, recipient_number: str = "33684950535"):
    """Test the complete flow: receive message -> process -> send reply."""
    print("=" * 60)
    print("Testing WhatsApp Webhook Text Message Flow")
    print("=" * 60)
    print()
    
    # Realistic WhatsApp Cloud API webhook payload
    webhook_payload = {
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
                                    "wa_id": recipient_number
                                }
                            ],
                            "messages": [
                                {
                                    "from": recipient_number,
                                    "id": "wamid.test_message_123",
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {
                                        "body": "Hello! This is a test message."
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
    
    webhook_url = f"{server_url.rstrip('/')}/whatsapp-webhook"
    
    print(f"Webhook URL: {webhook_url}")
    print(f"Recipient: +{recipient_number}")
    print("Sending test message: 'Hello! This is a test message.'")
    print()
    
    try:
        print("📤 Sending webhook request...")
        resp = requests.post(
            webhook_url,
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Status Code: {resp.status_code}")
        print()
        
        if resp.status_code == 200:
            try:
                response_data = resp.json()
                print("✅ Webhook responded successfully!")
                print()
                print("Response:")
                print(json.dumps(response_data, indent=2))
                print()
                
                if "sid" in response_data:
                    print(f"✅ Message ID: {response_data['sid']}")
                    print("   This means a reply was sent via WhatsApp Cloud API")
                
                if "reply" in response_data:
                    print(f"✅ Reply text: {response_data['reply']}")
                
                print()
                print("=" * 60)
                print("✅ TEST PASSED - Webhook is working correctly!")
                print("=" * 60)
                print()
                print("Next steps:")
                print("  1. Check your Flask server logs for processing details")
                print("  2. If you sent a real message, check WhatsApp for the reply")
                print("  3. If no reply in WhatsApp, check:")
                print("     - Recipient has opted in (sent message to business number)")
                print("     - WhatsApp Cloud API credentials are valid")
                print("     - Message was actually sent (check message ID)")
                return True
                
            except json.JSONDecodeError:
                print(f"⚠️  Response is not JSON: {resp.text[:200]}")
                return False
        else:
            print(f"❌ Webhook returned error status: {resp.status_code}")
            print(f"Response: {resp.text[:500]}")
            print()
            print("Common issues:")
            print("  - Webhook endpoint not accessible")
            print("  - Error in message processing")
            print("  - Missing credentials")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending webhook request: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print()
    print("🧪 WhatsApp Webhook Text Message Test")
    print()
    
    if len(sys.argv) < 2:
        print("Usage: python tests/test_webhook_text_message.py <server_url> [recipient_number]")
        print()
        print("Examples:")
        print("  python tests/test_webhook_text_message.py http://localhost:5000")
        print("  python tests/test_webhook_text_message.py https://dragonfly-interfilar-magaly.ngrok-free.dev")
        print("  python tests/test_webhook_text_message.py https://your-ngrok-url.ngrok-free.app 33684950535")
        print()
        sys.exit(1)
    
    server_url = sys.argv[1].rstrip("/")
    recipient_number = sys.argv[2] if len(sys.argv) > 2 else "33684950535"
    
    # Remove + if present
    if recipient_number.startswith("+"):
        recipient_number = recipient_number[1:]
    
    success = test_text_message_flow(server_url, recipient_number)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

