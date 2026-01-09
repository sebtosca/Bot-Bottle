"""Quick verification script to check test setup."""

import sys
from pathlib import Path

def check_imports():
    """Check if required modules can be imported."""
    import sys
    from pathlib import Path
    
    # Add project root to path (same as conftest.py)
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    errors = []
    
    try:
        import pytest
        print("✅ pytest imported successfully")
    except ImportError as e:
        errors.append(f"❌ pytest not installed: {e}")
    
    try:
        from endpoint.webhook.parser import parse_webhook_payload
        print("✅ endpoint.webhook.parser imported successfully")
    except ImportError as e:
        errors.append(f"❌ endpoint.webhook.parser import failed: {e}")
    
    try:
        from endpoint.webhook.models import WebhookEvent
        print("✅ endpoint.webhook.models imported successfully")
    except ImportError as e:
        errors.append(f"❌ endpoint.webhook.models import failed: {e}")
    
    try:
        from endpoint.security.validation import sanitize_filename
        print("✅ endpoint.security.validation imported successfully")
    except ImportError as e:
        errors.append(f"❌ endpoint.security.validation import failed: {e}")
    
    try:
        from flask import Flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        errors.append(f"❌ Flask not installed: {e}")
    
    if errors:
        print("\n❌ Import errors found:")
        for error in errors:
            print(f"  {error}")
        return False
    
    print("\n✅ All imports successful!")
    return True

def check_test_structure():
    """Check if test directory structure exists."""
    test_dir = Path(__file__).parent
    required_dirs = [
        "unit/webhook",
        "unit/security",
        "unit/middleware",
        "unit/helpers",
        "integration/webhook",
        "integration/routes",
        "integration/security",
        "e2e"
    ]
    
    missing = []
    for dir_path in required_dirs:
        full_path = test_dir / dir_path
        if not full_path.exists():
            missing.append(str(full_path))
    
    if missing:
        print("\n❌ Missing test directories:")
        for path in missing:
            print(f"  {path}")
        return False
    
    print("\n✅ Test directory structure is correct!")
    return True

if __name__ == "__main__":
    print("Verifying test setup...\n")
    
    imports_ok = check_imports()
    structure_ok = check_test_structure()
    
    if imports_ok and structure_ok:
        print("\n✅ Test setup verification complete!")
        sys.exit(0)
    else:
        print("\n❌ Test setup verification failed!")
        sys.exit(1)
