"""Shared pytest fixtures for models tests."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_product_ids():
    """Sample product IDs for testing."""
    return ["00001", "00002", "invalid_id", ""]
