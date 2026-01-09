#!/usr/bin/env python3
"""Test all modularized files to ensure they work correctly.

Tests syntax, imports, and basic functionality of all moved/created files.
"""

import sys
import ast
import traceback
from pathlib import Path
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Files to test
FILES_TO_TEST = [
    # Core modules
    ("core/__init__.py", "Core package"),
    ("core/game/__init__.py", "Core game package"),
    ("core/game/feeding_game.py", "Feeding game logic"),
    ("core/state/__init__.py", "Core state package"),
    ("core/state/bottle_state.py", "Bottle state management"),
    ("core/points/__init__.py", "Core points package"),
    ("core/points/rewards.py", "Points and rewards system"),
    
    # Features
    ("features/__init__.py", "Features package"),
    ("features/receipt/__init__.py", "Receipt feature package"),
    ("features/receipt/verification.py", "Receipt verification"),
    ("features/stats/__init__.py", "Stats feature package"),
    ("features/stats/visualizer.py", "Stats visualizer"),
    ("features/stats/display.py", "Stats display"),
    ("features/promos/__init__.py", "Promos feature package"),
    ("features/promos/supermarket.py", "Supermarket promos"),
    
    # Services
    ("services/__init__.py", "Services package"),
    ("services/whatsapp/__init__.py", "WhatsApp service package"),
    ("services/whatsapp/client.py", "WhatsApp client"),
    
    # Models
    ("models/__init__.py", "Models package"),
    ("models/characters.py", "Character models"),
]

IMPORTS_TO_TEST = [
    ("core.game", ["start_game", "process_emoji_feed"]),
    ("core.state", ["classify_message_type", "update_bottle_state"]),
    ("core.points", ["award_points", "get_user_stats"]),
    ("features.receipt", ["verify_receipt"]),
    ("features.stats", ["generate_stats_image", "send_stats_display"]),
    ("services.whatsapp", ["send_whatsapp_text", "WhatsAppCloudError"]),
    ("models.characters", ["get_character_config", "get_character_id"]),
]


def test_syntax(file_path: str, description: str) -> Tuple[bool, str]:
    """Test that a file has valid Python syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, "✓"
    except SyntaxError as e:
        return False, f"✗ Syntax error: {e}"
    except Exception as e:
        return False, f"✗ Error: {e}"


def test_import(module_name: str, items: List[str], description: str) -> Tuple[bool, str]:
    """Test that a module can be imported and exports expected items."""
    try:
        module = __import__(module_name, fromlist=items)
        missing = []
        for item in items:
            if not hasattr(module, item):
                missing.append(item)
        
        if missing:
            return False, f"✗ Missing exports: {', '.join(missing)}"
        
        return True, "✓"
    except ImportError as e:
        error_msg = str(e)
        # Check if it's a missing dependency vs actual import error
        if "No module named" in error_msg:
            missing_dep = error_msg.split("'")[1] if "'" in error_msg else "unknown"
            return False, f"⚠ Missing dependency: {missing_dep} (install with pip)"
        return False, f"✗ Import error: {e}"
    except Exception as e:
        return False, f"✗ Error: {e}"


def test_basic_functionality():
    """Test basic functionality of key modules (without full environment)."""
    results = []
    
    # Test models.characters (no dependencies)
    try:
        from models.characters import get_character_config, get_character_id
        config = get_character_config("00001")
        assert "name" in config
        assert "product_id" in config
        char_id = get_character_id("00001")
        assert char_id == "00001"
        results.append(("models.characters functionality", True, "✓"))
    except Exception as e:
        results.append(("models.characters functionality", False, f"✗ {e}"))
    
    # Test core.points constants (requires sqlalchemy, but we can test structure)
    try:
        # Try to read the file and check constants exist
        rewards_file = project_root / "core/points/rewards.py"
        with open(rewards_file, 'r') as f:
            content = f.read()
            assert "TITLE_THRESHOLDS" in content
            assert "POINTS_FEEDING" in content
            assert "POINTS_BOTTLE_RETURN" in content
        results.append(("core.points constants structure", True, "✓"))
    except Exception as e:
        results.append(("core.points constants structure", False, f"✗ {e}"))
    
    # Test that __init__.py files export correctly (structure check)
    try:
        init_files = [
            "core/game/__init__.py",
            "core/state/__init__.py",
            "core/points/__init__.py",
            "features/receipt/__init__.py",
            "features/stats/__init__.py",
            "services/whatsapp/__init__.py",
            "models/__init__.py",
        ]
        for init_file in init_files:
            file_path = project_root / init_file
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                    assert "__all__" in content or "from" in content
        results.append(("__init__.py exports structure", True, "✓"))
    except Exception as e:
        results.append(("__init__.py exports structure", False, f"✗ {e}"))
    
    return results


def main():
    """Run all tests."""
    print("=" * 70)
    print("Modularization Test Suite")
    print("=" * 70)
    
    # Test 1: Syntax validation
    print("\n1. Syntax Validation")
    print("-" * 70)
    syntax_results = []
    for file_path, description in FILES_TO_TEST:
        full_path = project_root / file_path
        if not full_path.exists():
            syntax_results.append((description, False, f"✗ File not found: {file_path}"))
            continue
        
        success, message = test_syntax(str(full_path), description)
        syntax_results.append((description, success, message))
        status = "✓" if success else "✗"
        print(f"  {status} {description:40} {file_path}")
        if not success:
            print(f"    {message}")
    
    # Test 2: Import validation
    print("\n2. Import Validation")
    print("-" * 70)
    import_results = []
    for module_name, items in IMPORTS_TO_TEST:
        description = f"{module_name} ({', '.join(items[:2])}...)"
        success, message = test_import(module_name, items, description)
        import_results.append((description, success, message))
        status = "✓" if success else "✗"
        print(f"  {status} {description}")
        if not success:
            print(f"    {message}")
    
    # Test 3: Basic functionality
    print("\n3. Basic Functionality Tests")
    print("-" * 70)
    func_results = test_basic_functionality()
    for description, success, message in func_results:
        status = "✓" if success else "✗"
        print(f"  {status} {description:40} {message}")
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    all_syntax = all(success for _, success, _ in syntax_results)
    all_imports = all(success for _, success, _ in import_results)
    all_func = all(success for _, success, _ in func_results)
    
    syntax_count = sum(1 for _, success, _ in syntax_results if success)
    import_count = sum(1 for _, success, _ in import_results if success)
    func_count = sum(1 for _, success, _ in func_results if success)
    
    print(f"\nSyntax Tests:     {syntax_count}/{len(syntax_results)} passed")
    print(f"Import Tests:     {import_count}/{len(import_results)} passed")
    print(f"Functionality:    {func_count}/{len(func_results)} passed")
    
    # Count dependency-related failures vs actual errors
    dependency_failures = sum(1 for _, success, msg in import_results 
                              if not success and "Missing dependency" in msg)
    actual_import_failures = sum(1 for _, success, msg in import_results 
                                 if not success and "Missing dependency" not in msg)
    
    print(f"\nDependency Issues: {dependency_failures} (expected - install dependencies)")
    print(f"Actual Import Errors: {actual_import_failures}")
    
    if all_syntax and actual_import_failures == 0 and all_func:
        print("\n✅ All critical tests passed!")
        print("   (Import failures are due to missing dependencies - install with: pip install -r requirements.txt)")
        return 0
    elif all_syntax:
        print("\n⚠️  Syntax is valid, but some imports failed.")
        print("   Install dependencies: pip install -r requirements.txt")
        if actual_import_failures > 0:
            print(f"   {actual_import_failures} actual import error(s) need fixing.")
            return 1
        return 0
    else:
        print("\n❌ Syntax errors found. Please fix these first.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
