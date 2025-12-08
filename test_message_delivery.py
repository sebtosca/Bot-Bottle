#!/usr/bin/env python3
"""Diagnostic script to test WhatsApp message delivery and verify recipient configuration.

This script helps diagnose why messages might not be delivered even when
the API returns success. It checks:
- Phone number format (E.164)
- API response for errors/warnings
- Recipient allowed list status
"""

import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from whatsapp_cloud_client import send_whatsapp_text, WhatsAppCloudError


def validate_phone_number(phone: str) -> tuple[bool, Optional[str]]:
    """Validate phone number format (E.164).
    
    Returns:
        (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is empty"
    
    if not phone.startswith("+"):
        return False, "Phone number must start with '+' (E.164 format)"
    
    # Remove + and check if rest is digits
    digits = phone[1:]
    if not digits.isdigit():
        return False, "Phone number must contain only digits after '+'"
    
    if len(digits) < 7 or len(digits) > 15:
        return False, f"Phone number length invalid: {len(digits)} digits (should be 7-15)"
    
    return True, None


def test_message_delivery(recipient_number: str, test_message: str = "Test message from BotBottle") -> bool:
    """Test sending a message and diagnose delivery issues.
    
    Returns:
        True if message was sent successfully, False otherwise
    """
    print("=" * 60)
    print("WhatsApp Message Delivery Diagnostic")
    print("=" * 60)
    print()
    
    # Check configuration
    print("1. Checking configuration...")
    if not WHATSAPP_ACCESS_TOKEN:
        print("   ❌ WHATSAPP_ACCESS_TOKEN not set")
        print("   Set it in your .env file or environment")
        return False
    else:
        print("   ✅ WHATSAPP_ACCESS_TOKEN is set")
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("   ❌ WHATSAPP_PHONE_NUMBER_ID not set")
        print("   Set it in your .env file or environment")
        return False
    else:
        print(f"   ✅ WHATSAPP_PHONE_NUMBER_ID is set: {WHATSAPP_PHONE_NUMBER_ID}")
    
    print()
    
    # Validate phone number
    print("2. Validating phone number format...")
    is_valid, error_msg = validate_phone_number(recipient_number)
    if not is_valid:
        print(f"   ❌ Invalid phone number format: {error_msg}")
        print()
        print("   Phone numbers must be in E.164 format:")
        print("   - Start with '+' followed by country code")
        print("   - Example: +33684950535 (France)")
        print("   - Example: +14155552671 (USA)")
        print()
        print(f"   Your number: {recipient_number}")
        return False
    else:
        print(f"   ✅ Phone number format is valid: {recipient_number}")
    
    print()
    
    # Try sending message
    print("3. Attempting to send test message...")
    print(f"   To: {recipient_number}")
    print(f"   Message: {test_message}")
    print()
    
    try:
        message_id = send_whatsapp_text(recipient_number, test_message)
        print(f"   ✅ Message sent successfully!")
        print(f"   Message ID: {message_id}")
        print()
        print("   If you don't receive the message, check:")
        print("   1. Is the recipient number in your allowed list?")
        print("      → Go to Meta Developer Console → WhatsApp → API Setup")
        print("      → Under 'Add a recipient phone number', add your number")
        print()
        print("   2. Is your WhatsApp Business Account in test mode?")
        print("      → Test mode only allows sending to numbers in the allowed list")
        print()
        print("   3. Wait a few seconds - messages can take time to deliver")
        return True
        
    except WhatsAppCloudError as e:
        print(f"   ❌ WhatsApp API Error: {e}")
        if e.error_code:
            print(f"   Error code: {e.error_code}")
        if e.error_subcode:
            print(f"   Error subcode: {e.error_subcode}")
        if e.full_response:
            print(f"   Full response: {e.full_response}")
        print()
        
        # Provide specific guidance based on error code
        if e.error_code == "131030" or e.error_subcode == "131030":
            print("   ⚠️  RECIPIENT NOT IN ALLOWED LIST")
            print()
            print("   This is the most common issue in test mode.")
            print("   To fix:")
            print("   1. Go to: https://developers.facebook.com/")
            print("   2. Navigate to your WhatsApp app → API Setup")
            print("   3. Under 'Add a recipient phone number', add:")
            print(f"      {recipient_number}")
            print("   4. Save and wait a few seconds")
            print("   5. Try sending again")
            print()
            print("   Note: In test mode, you can only send messages to")
            print("         phone numbers in your allowed list.")
            
        elif e.error_code == "131026" or e.error_subcode == "131026":
            print("   ⚠️  INVALID PHONE NUMBER")
            print()
            print("   The phone number format is incorrect.")
            print("   Make sure it's in E.164 format: +[country code][number]")
            print(f"   Your number: {recipient_number}")
            
        elif e.error_code == "131048" or e.error_subcode == "131048":
            print("   ⚠️  RATE LIMIT EXCEEDED")
            print()
            print("   You've sent too many messages too quickly.")
            print("   Wait a few minutes before trying again.")
            
        else:
            print("   ⚠️  UNKNOWN ERROR")
            print("   Check the error message above for details.")
            print("   Common issues:")
            print("   - Invalid access token")
            print("   - Invalid phone number ID")
            print("   - API version mismatch")
            print("   - Network issues")
        
        return False
        
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python test_message_delivery.py <PHONE_NUMBER> [MESSAGE]")
        print()
        print("Example:")
        print("  python test_message_delivery.py +33684950535")
        print("  python test_message_delivery.py +33684950535 'Hello, this is a test!'")
        print()
        print("Phone number must be in E.164 format (e.g., +33684950535)")
        return 1
    
    recipient = sys.argv[1]
    test_message = sys.argv[2] if len(sys.argv) > 2 else "Test message from BotBottle diagnostic script"
    
    success = test_message_delivery(recipient, test_message)
    
    print()
    print("=" * 60)
    if success:
        print("✅ Diagnostic completed - message was sent")
        print("   Check your WhatsApp to see if you received it")
    else:
        print("❌ Diagnostic completed - message was not sent")
        print("   Follow the instructions above to fix the issue")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

