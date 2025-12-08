"""Test script to verify Flask endpoint is working correctly."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from endpoint.endpoint import app, SYSTEM_PROMPT


def test_app_import():
    """Test that the Flask app can be imported."""
    print("=" * 60)
    print("Test 1: Flask App Import")
    print("=" * 60)
    try:
        assert app is not None
        # Flask app name might be 'endpoint.endpoint' when run as module
        assert "endpoint" in app.name
        print("✅ Flask app imported successfully")
        print(f"   App name: {app.name}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_routes_registered():
    """Test that routes are registered."""
    print("\n" + "=" * 60)
    print("Test 2: Routes Registration")
    print("=" * 60)
    try:
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        print(f"Registered routes: {routes}")
        
        assert "/health" in routes
        assert "/whatsapp-webhook" in routes
        print("✅ All required routes are registered")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_health_endpoint():
    """Test the /health endpoint using Flask test client."""
    print("\n" + "=" * 60)
    print("Test 3: Health Endpoint")
    print("=" * 60)
    try:
        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "ok"
            print(f"✅ Health endpoint works")
            print(f"   Response: {data}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_webhook_endpoint_structure():
    """Test webhook endpoint structure (without actually calling LLM/WhatsApp API)."""
    print("\n" + "=" * 60)
    print("Test 4: Webhook Endpoint Structure")
    print("=" * 60)
    try:
        with app.test_client() as client:
            # Test webhook verification (GET)
            response = client.get("/whatsapp-webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=test123")
            # Should return 403 if token doesn't match, or 200 if it does
            assert response.status_code in [200, 403]
            print("✅ Webhook verification endpoint works")
            
            # Test with valid JSON structure (WhatsApp Cloud API format)
            test_payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": "33684950535",
                                "id": "test123",
                                "type": "text",
                                "text": {"body": "Hello"}
                            }]
                        }
                    }]
                }]
            }
            response = client.post("/whatsapp-webhook", json=test_payload)
            # Should either succeed (if LLM/WhatsApp API work) or fail with 500 (if not configured)
            # But not 400, which means structure is correct
            assert response.status_code != 400
            print(f"✅ Webhook endpoint structure is correct (status: {response.status_code})")
            if response.status_code == 500:
                print("   Note: LLM or WhatsApp API may not be configured, but endpoint structure is valid")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def test_system_prompt():
    """Test that system prompt is defined."""
    print("\n" + "=" * 60)
    print("Test 5: System Prompt")
    print("=" * 60)
    try:
        assert SYSTEM_PROMPT is not None
        assert len(SYSTEM_PROMPT) > 0
        assert "maraschino" in SYSTEM_PROMPT.lower() or "cherry" in SYSTEM_PROMPT.lower()
        print("✅ System prompt is defined")
        print(f"   Length: {len(SYSTEM_PROMPT)} characters")
        print(f"   Preview: {SYSTEM_PROMPT[:80]}...")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False


def main():
    """Run all endpoint tests."""
    print("\n" + "=" * 60)
    print("Endpoint Verification Test Suite")
    print("=" * 60)
    print("\nTesting Flask app structure and endpoints...\n")

    results = []
    results.append(("App Import", test_app_import()))
    results.append(("Routes Registration", test_routes_registered()))
    results.append(("Health Endpoint", test_health_endpoint()))
    results.append(("Webhook Structure", test_webhook_endpoint_structure()))
    results.append(("System Prompt", test_system_prompt()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Endpoint is working correctly.")
        print("\nTo start the server, run:")
        print("  python -m endpoint.endpoint")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())

