"""Check webhook status and configuration."""

import sys
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import WHATSAPP_VERIFY_TOKEN, WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID


def check_webhook_verification():
    """Test webhook verification endpoint."""
    print("=" * 60)
    print("Testing Webhook Verification")
    print("=" * 60)
    
    if not WHATSAPP_VERIFY_TOKEN:
        print("❌ WHATSAPP_VERIFY_TOKEN not set")
        return False
    
    # Test with ngrok URL
    ngrok_url = "https://dragonfly-interfilar-magaly.ngrok-free.dev"
    webhook_url = f"{ngrok_url}/whatsapp-webhook"
    
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": WHATSAPP_VERIFY_TOKEN,
        "hub.challenge": "test_challenge_123"
    }
    
    print(f"URL: {webhook_url}")
    print(f"Verify Token: {WHATSAPP_VERIFY_TOKEN[:10]}...")
    print()
    
    try:
        resp = requests.get(webhook_url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        if resp.status_code == 200 and resp.text == "test_challenge_123":
            print("✅ Webhook verification working!")
            return True
        else:
            print("❌ Webhook verification failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def check_webhook_subscription():
    """Check webhook subscription status via API."""
    print()
    print("=" * 60)
    print("Checking Webhook Subscription (via API)")
    print("=" * 60)
    
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("⚠️  Cannot check subscription - missing credentials")
        return
    
    # Get app ID from phone number ID (this is a workaround)
    # In production, you'd use the app ID directly
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Phone number info retrieved")
            print(f"   Display name: {data.get('display_phone_number', 'N/A')}")
        else:
            print(f"⚠️  Could not retrieve phone number info: {resp.status_code}")
    except Exception as e:
        print(f"⚠️  Error checking subscription: {e}")


def main():
    """Main diagnostic function."""
    print()
    print("🔍 Webhook Status Check")
    print()
    
    verification_ok = check_webhook_verification()
    check_webhook_subscription()
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    
    if verification_ok:
        print("✅ Webhook endpoint is accessible and verification works")
        print()
        print("Next steps:")
        print("  1. Go to Meta Developer Console → WhatsApp → Configuration")
        print("  2. Verify webhook URL is set to:")
        print("     https://dragonfly-interfilar-magaly.ngrok-free.dev/whatsapp-webhook")
        print("  3. Verify token is set to: AIARTPROGRAM")
        print("  4. Under 'Webhook fields', ensure 'messages' is subscribed")
        print("  5. Send a test message from WhatsApp")
    else:
        print("❌ Webhook verification failed")
        print("   Check that Flask server is running and ngrok is active")


if __name__ == "__main__":
    main()

