"""Test script to verify Mistral AI API integration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.llama_client import generate_reply
from config import LLM_PROVIDER, MISTRAL_API_KEY, MISTRAL_MODEL_NAME


def test_mistral_integration():
    """Test Mistral AI API integration."""
    print("=" * 60)
    print("Mistral AI API Integration Test")
    print("=" * 60)
    
    print(f"\nConfiguration:")
    print(f"  LLM_PROVIDER: {LLM_PROVIDER}")
    print(f"  MISTRAL_API_KEY: {'Set' if MISTRAL_API_KEY else 'NOT SET'}")
    print(f"  MISTRAL_MODEL_NAME: {MISTRAL_MODEL_NAME}")
    
    if not MISTRAL_API_KEY:
        print("\n❌ MISTRAL_API_KEY is not set in .env file")
        print("   Get your API key from: https://console.mistral.ai/")
        print("   Add to .env: MISTRAL_API_KEY=your_key_here")
        return False
    
    if LLM_PROVIDER.lower() != "mistral":
        print(f"\n⚠️  Warning: LLM_PROVIDER is set to '{LLM_PROVIDER}', not 'mistral'")
        print("   The test will still work, but make sure LLM_PROVIDER=mistral in .env")
        print("   to use Mistral AI in production.")
    
    system_prompt = (
        "You are a digital Maraschino cherry. "
        "You are cheery, playful, and a bit of a diva. "
        "Keep replies short and conversational (1-2 sentences)."
    )
    
    conversation_history = [
        {"role": "user", "content": "Hello! How are you?"}
    ]
    
    try:
        print("\nTesting Mistral AI API...")
        print(f"Using model: {MISTRAL_MODEL_NAME}")
        
        reply = generate_reply(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            max_tokens=100
        )
        
        print(f"\n✅ SUCCESS!")
        print(f"   Provider: {LLM_PROVIDER}")
        print(f"   Model: {MISTRAL_MODEL_NAME}")
        print(f"   Reply: {reply}")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_mistral_integration()
    exit(0 if success else 1)

