"""Test script to verify WhatsApp Cloud API setup and send a test message.

This script checks:
1. All required credentials are present
2. API connectivity
3. Ability to send a test message

Usage:
    python tests/test_whatsapp_cloud_api.py <recipient_phone_number>
    
Example:
    python tests/test_whatsapp_cloud_api.py +33684950535
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    WHATSAPP_ACCOUNT_ID,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_ACCESS_TOKEN,
)
from whatsapp_cloud_client import send_whatsapp_text, WhatsAppCloudError


def check_credentials():
    """Check if all required credentials are present."""
    print("=" * 60)
    print("Checking WhatsApp Cloud API Credentials")
    print("=" * 60)
    
    missing = []
    
    if WHATSAPP_ACCOUNT_ID:
        print(f"✅ WHATSAPP_ACCOUNT_ID: {WHATSAPP_ACCOUNT_ID[:10]}...")
    else:
        print("⚠️  WHATSAPP_ACCOUNT_ID: Missing (optional for sending messages)")
    
    if WHATSAPP_PHONE_NUMBER_ID:
        print(f"✅ WHATSAPP_PHONE_NUMBER_ID: {WHATSAPP_PHONE_NUMBER_ID}")
    else:
        print("❌ WHATSAPP_PHONE_NUMBER_ID: Missing (REQUIRED)")
        missing.append("WHATSAPP_PHONE_NUMBER_ID")
    
    if WHATSAPP_ACCESS_TOKEN:
        # Show first and last 4 chars for security
        token_preview = f"{WHATSAPP_ACCESS_TOKEN[:4]}...{WHATSAPP_ACCESS_TOKEN[-4:]}" if len(WHATSAPP_ACCESS_TOKEN) > 8 else "***"
        print(f"✅ WHATSAPP_ACCESS_TOKEN: {token_preview}")
    else:
        print("❌ WHATSAPP_ACCESS_TOKEN: Missing (REQUIRED)")
        missing.append("WHATSAPP_ACCESS_TOKEN")
    
    print()
    
    if missing:
        print(f"❌ Missing required credentials: {', '.join(missing)}")
        print("   Please add them to your .env file")
        return False
    
    print("✅ All required credentials are present!")
    return True


def test_send_message(recipient_number: str):
    """Test sending a message via WhatsApp Cloud API."""
    print("=" * 60)
    print("Testing WhatsApp Cloud API Message Sending")
    print("=" * 60)
    
    # Normalize phone number (remove whatsapp: prefix if present)
    if recipient_number.startswith("whatsapp:"):
        recipient_number = recipient_number.replace("whatsapp:", "")
    
    # Ensure it starts with +
    if not recipient_number.startswith("+"):
        recipient_number = f"+{recipient_number}"
    
    print(f"Recipient: {recipient_number}")
    print(f"Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print()
    
    test_message = "🧪 Test message from BotBottle WhatsApp Cloud API! If you receive this, the API is working correctly! ✅"
    
    try:
        print("📤 Sending test message...")
        message_id = send_whatsapp_text(recipient_number, test_message)
        print()
        print("=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"Message ID: {message_id}")
        print(f"Message sent to: {recipient_number}")
        print()
        print("📱 Check the recipient's WhatsApp to confirm delivery.")
        print()
        print("Next steps:")
        print("  1. Verify the message appears in WhatsApp")
        print("  2. If successful, proceed with webhook migration")
        print("  3. If failed, check:")
        print("     - Phone number format (must be E.164: +[country][number])")
        print("     - Recipient has opted in to receive messages")
        print("     - Access token has proper permissions")
        return True
        
    except WhatsAppCloudError as e:
        print()
        print("=" * 60)
        print("❌ ERROR: Failed to send message")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  1. Invalid phone number format (must be E.164: +[country][number])")
        print("  2. Recipient hasn't opted in to receive messages")
        print("  3. Access token expired or invalid")
        print("  4. Phone number ID incorrect")
        print("  5. Rate limiting (wait a few minutes)")
        return False
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print()
    print("🧪 WhatsApp Cloud API Test Script")
    print()
    
    # Check credentials first
    if not check_credentials():
        print()
        print("Please fix the missing credentials and try again.")
        sys.exit(1)
    
    # Get recipient number from command line
    if len(sys.argv) < 2:
        print()
        print("Usage: python tests/test_whatsapp_cloud_api.py <recipient_phone_number>")
        print()
        print("Example:")
        print("  python tests/test_whatsapp_cloud_api.py +33684950535")
        print("  python tests/test_whatsapp_cloud_api.py 33684950535")
        print()
        print("Note: The recipient must have opted in to receive messages")
        print("      from your WhatsApp Business Account.")
        sys.exit(1)
    
    recipient = sys.argv[1]
    
    # Test sending message
    success = test_send_message(recipient)
    
    print()
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

