#!/usr/bin/env python3
"""Test runner for notification tests to capture errors."""

import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import pytest
    
    # Run the tests and capture output
    exit_code = pytest.main([
        "endpoint/tests/unit/helpers/test_notifications.py",
        "-v",
        "--tb=short"
    ])
    
    sys.exit(exit_code)
    
except ImportError as e:
    print(f"❌ Error importing pytest: {e}")
    print("Please install pytest: pip install pytest")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    traceback.print_exc()
    sys.exit(1)
