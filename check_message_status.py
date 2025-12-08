#!/usr/bin/env python3
"""Check WhatsApp message delivery status and diagnose delivery issues.

This script helps diagnose why messages might not be delivered even when
the API returns success and the number is in the allowed list.
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID
from whatsapp_cloud_client import send_whatsapp_text, WhatsAppCloudError
import requests


def check_24_hour_window(phone_number: str):
    """Check if recipient has messaged you within 24 hours.
    
    In test mode, you can only send messages to users who have messaged
    you first within the last 24 hours (24-hour messaging window).
    """
    print()
    print("=" * 60)
    print("24-Hour Messaging Window Check")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: In test mode, you can only send messages to")
    print("   recipients who have messaged you FIRST within the last 24 hours.")
    print()
    print("   This is called the '24-hour messaging window'.")
    print()
    print(f"   To receive messages to {phone_number}:")
    print("   1. Send a message FROM that WhatsApp number TO your business number")
    print("   2. Wait for the webhook to receive it")
    print("   3. Then you can reply (within 24 hours)")
    print()
    print("   If the recipient hasn't messaged you first, WhatsApp")
    print("   will accept the message but won't deliver it.")
    print("=" * 60)
    print()


def check_number_format_in_allowed_list(phone_number: str):
    """Provide guidance on checking number format in allowed list."""
    print()
    print("=" * 60)
    print("Number Format Check")
    print("=" * 60)
    print()
    print("Verify the number format in Meta Developer Console:")
    print()
    print(f"   Your number: {phone_number}")
    print()
    print("   In Meta Developer Console → WhatsApp → API Setup:")
    print("   - Check the 'To' field in the allowed recipients list")
    print("   - It should match EXACTLY: {phone_number}")
    print("   - Common mismatches:")
    print("     * With/without '+' prefix")
    print("     * With/without spaces")
    print("     * Different country code format")
    print()
    print("   If formats don't match, remove and re-add the number.")
    print("=" * 60)
    print()


def main():
    """Main diagnostic function."""
    if len(sys.argv) < 2:
        print("Usage: python check_message_status.py <PHONE_NUMBER>")
        print()
        print("Example:")
        print("  python check_message_status.py +33684950535")
        print()
        print("This script helps diagnose delivery issues when:")
        print("  - API returns success (message ID)")
        print("  - Number is in allowed list")
        print("  - But message is not received")
        return 1
    
    phone_number = sys.argv[1]
    
    print("=" * 60)
    print("WhatsApp Message Delivery Diagnostic")
    print("=" * 60)
    print()
    print("Diagnosing why messages aren't being delivered...")
    print()
    
    # Check 24-hour window
    check_24_hour_window(phone_number)
    
    # Check number format
    check_number_format_in_allowed_list(phone_number)
    
    # Try sending a test message
    print("=" * 60)
    print("Sending Test Message")
    print("=" * 60)
    print()
    
    try:
        message_id = send_whatsapp_text(phone_number, "Test message - please check if you receive this")
        print(f"✅ Message sent successfully!")
        print(f"   Message ID: {message_id}")
        print()
        print("If you don't receive the message, the most likely causes are:")
        print()
        print("1. ⚠️  24-HOUR MESSAGING WINDOW (Most Common)")
        print("   - Recipient must message you FIRST")
        print("   - Then you can reply within 24 hours")
        print("   - In test mode, this restriction is strict")
        print()
        print("2. ⚠️  Number format mismatch in allowed list")
        print("   - Check Meta Console that the number matches exactly")
        print("   - Remove and re-add if needed")
        print()
        print("3. ⚠️  Delivery delay")
        print("   - Wait 30-60 seconds")
        print("   - Check WhatsApp app is connected")
        print()
        print("4. ⚠️  WhatsApp Business Account restrictions")
        print("   - Check Meta Console for any warnings")
        print("   - Verify account is active")
        print()
        return 0
        
    except WhatsAppCloudError as e:
        print(f"❌ Error: {e}")
        if e.error_code:
            print(f"   Error code: {e.error_code}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

