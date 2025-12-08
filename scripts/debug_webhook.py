"""Debug script to check webhook configuration and test message sending."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    MISTRAL_API_KEY,
    LLM_PROVIDER,
)
from whatsapp_cloud_client import send_whatsapp_text
from llm.llama_client import generate_reply


def test_llm():
    """Test if LLM is working."""
    print("=" * 60)
    print("Testing LLM Configuration")
    print("=" * 60)
    
    if LLM_PROVIDER == "mistral":
        if not MISTRAL_API_KEY:
            print("❌ MISTRAL_API_KEY not set")
            return False
        print(f"✅ LLM Provider: {LLM_PROVIDER}")
        print(f"✅ MISTRAL_API_KEY: {MISTRAL_API_KEY[:10]}...")
    else:
        print(f"⚠️  LLM Provider: {LLM_PROVIDER} (must be 'mistral')")
    
    try:
        reply = generate_reply(
            system_prompt="You are a helpful assistant.",
            conversation_history=[{"role": "user", "content": "Say hello"}],
            max_tokens=20
        )
        print(f"✅ LLM test successful")
        print(f"   Reply: {reply}")
        return True
    except Exception as e:
        print(f"❌ LLM test failed: {e}")
        return False


def test_whatsapp_send():
    """Test sending a WhatsApp message."""
    print()
    print("=" * 60)
    print("Testing WhatsApp Message Sending")
    print("=" * 60)
    
    if not WHATSAPP_ACCESS_TOKEN:
        print("❌ WHATSAPP_ACCESS_TOKEN not set")
        return False
    
    if not WHATSAPP_PHONE_NUMBER_ID:
        print("❌ WHATSAPP_PHONE_NUMBER_ID not set")
        return False
    
    print(f"✅ Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    
    # Test with a simple message
    test_number = "+33684950535"
    test_message = "Test message from debug script"
    
    try:
        print(f"📤 Sending test message to {test_number}...")
        msg_id = send_whatsapp_text(test_number, test_message)
        print(f"✅ Message sent successfully!")
        print(f"   Message ID: {msg_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to send message: {e}")
        return False


def main():
    """Run all diagnostic tests."""
    print()
    print("🔍 WhatsApp Webhook Diagnostic Tool")
    print()
    
    llm_ok = test_llm()
    whatsapp_ok = test_whatsapp_send()
    
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"LLM: {'✅ Working' if llm_ok else '❌ Not working'}")
    print(f"WhatsApp API: {'✅ Working' if whatsapp_ok else '❌ Not working'}")
    
    if not llm_ok:
        print()
        print("⚠️  LLM is not working. No replies will be generated.")
        print("   Set MISTRAL_API_KEY in .env to enable LLM responses.")
    
    if not whatsapp_ok:
        print()
        print("❌ WhatsApp API is not working. Check your credentials.")
    
    print()
    if llm_ok and whatsapp_ok:
        print("✅ All systems operational!")
    else:
        print("⚠️  Some systems need attention. Check the errors above.")


if __name__ == "__main__":
    main()

