"""Quick script to check if WhatsApp Cloud API credentials are configured.

This script only checks if the credentials are present in the environment,
it does not make any API calls.

Usage:
    python scripts/check_whatsapp_credentials.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    WHATSAPP_ACCOUNT_ID,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_VERIFY_TOKEN,
)


def main():
    """Check WhatsApp Cloud API credentials."""
    print()
    print("=" * 60)
    print("WhatsApp Cloud API Credentials Check")
    print("=" * 60)
    print()
    
    all_present = True
    
    # Check Account ID (optional for sending, but good to have)
    if WHATSAPP_ACCOUNT_ID:
        print(f"✅ WHATSAPP_ACCOUNT_ID: {WHATSAPP_ACCOUNT_ID}")
    else:
        print("⚠️  WHATSAPP_ACCOUNT_ID: Not set (optional for sending messages)")
    
    # Check Phone Number ID (required for sending)
    if WHATSAPP_PHONE_NUMBER_ID:
        print(f"✅ WHATSAPP_PHONE_NUMBER_ID: {WHATSAPP_PHONE_NUMBER_ID}")
    else:
        print("❌ WHATSAPP_PHONE_NUMBER_ID: Missing (REQUIRED for sending messages)")
        all_present = False
    
    # Check Access Token (required for sending)
    if WHATSAPP_ACCESS_TOKEN:
        # Show first and last 4 chars for security
        if len(WHATSAPP_ACCESS_TOKEN) > 8:
            token_preview = f"{WHATSAPP_ACCESS_TOKEN[:4]}...{WHATSAPP_ACCESS_TOKEN[-4:]}"
        else:
            token_preview = "***"
        print(f"✅ WHATSAPP_ACCESS_TOKEN: {token_preview}")
    else:
        print("❌ WHATSAPP_ACCESS_TOKEN: Missing (REQUIRED for sending messages)")
        all_present = False
    
    # Check Verify Token (required for webhooks)
    if WHATSAPP_VERIFY_TOKEN:
        print(f"✅ WHATSAPP_VERIFY_TOKEN: {WHATSAPP_VERIFY_TOKEN[:10]}...")
    else:
        print("⚠️  WHATSAPP_VERIFY_TOKEN: Not set (REQUIRED for webhook verification)")
        print("   You'll need this when setting up webhooks in Meta Developer Console")
    
    print()
    print("=" * 60)
    
    if all_present:
        print("✅ All required credentials for sending messages are present!")
        print()
        print("Next step: Test sending a message with:")
        print("  python tests/test_whatsapp_cloud_api.py <recipient_phone_number>")
    else:
        print("❌ Some required credentials are missing.")
        print()
        print("Please add the missing credentials to your .env file:")
        print("  WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id")
        print("  WHATSAPP_ACCESS_TOKEN=your_access_token")
        print("  WHATSAPP_ACCOUNT_ID=your_account_id  (optional)")
        print("  WHATSAPP_VERIFY_TOKEN=your_verify_token  (for webhooks)")
    
    print()
    return all_present


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

