"""End-to-end tests for LLM client."""

import pytest
import os
from llm.llama_client import generate_reply


@pytest.mark.e2e
@pytest.mark.skipif(
    not os.environ.get("MISTRAL_API_KEY"),
    reason="MISTRAL_API_KEY not set - skipping E2E test"
)
class TestLLME2E:
    """End-to-end tests for LLM client with real API."""
    
    def test_generate_reply_e2e(self):
        """Test generating reply with real Mistral API."""
        conversation = [
            {"role": "user", "content": "Hello, this is an E2E test!"}
        ]
        
        result = generate_reply(
            "You are a helpful assistant. Respond briefly.",
            conversation,
            None,
            temperature=0.7,
            max_tokens=50
        )
        
        assert isinstance(result, str)
        assert len(result.strip()) > 0
        # Verify it's a reasonable response (not empty, not error message)
        assert len(result) < 500  # Should be brief
