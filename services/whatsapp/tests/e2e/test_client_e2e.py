"""End-to-end tests for WhatsApp client."""

import pytest
import os
from services.whatsapp.client import send_whatsapp_text, WhatsAppCloudError


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.environ.get("WHATSAPP_ACCESS_TOKEN") or not os.environ.get("WHATSAPP_PHONE_NUMBER_ID"),
    reason="WhatsApp credentials not set - skipping E2E test"
)
class TestWhatsAppE2E:
    """End-to-end tests for WhatsApp client with real API (if available)."""
    
    @pytest.mark.skip(reason="Requires real API credentials and test phone number")
    def test_send_text_e2e(self):
        """Test sending actual text message (requires test credentials)."""
        # This test would send a real message if credentials are available
        # For safety, it's skipped by default
        test_phone = os.environ.get("TEST_WHATSAPP_PHONE", None)
        if not test_phone:
            pytest.skip("TEST_WHATSAPP_PHONE not set")
        
        message_id = send_whatsapp_text(test_phone, "E2E test message")
        
        assert message_id is not None
        assert len(message_id) > 0
