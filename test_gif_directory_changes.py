#!/usr/bin/env python3
"""Test script to verify GIF directory changes are working correctly."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.characters import get_character_config, CHARACTERS
from endpoint.routes.static_files import register_static_routes
from flask import Flask

def test_character_configs():
    """Test that character configurations use correct GIF directories."""
    print("=" * 60)
    print("Testing Character Configurations")
    print("=" * 60)
    
    cherry = get_character_config("00001")
    pompon = get_character_config("00002")
    
    print(f"\n🍒 Cherry (00001):")
    print(f"   gif_dir: {cherry['gif_dir']}")
    
    print(f"\n🍎 Pompon (00002):")
    print(f"   gif_dir: {pompon['gif_dir']}")
    
    # Verify
    assert cherry['gif_dir'] == 'Cherry_GIF', f"Expected 'Cherry_GIF', got '{cherry['gif_dir']}'"
    assert pompon['gif_dir'] == 'pompon_GIF', f"Expected 'pompon_GIF', got '{pompon['gif_dir']}'"
    
    print("\n✅ Character configurations are correct!")
    return True


def test_gif_directories_exist():
    """Test that GIF directories exist."""
    print("\n" + "=" * 60)
    print("Testing GIF Directory Existence")
    print("=" * 60)
    
    cherry = get_character_config("00001")
    pompon = get_character_config("00002")
    
    cherry_dir = project_root / cherry['gif_dir']
    pompon_dir = project_root / pompon['gif_dir']
    
    print(f"\n🍒 Cherry GIF directory: {cherry_dir}")
    print(f"   Exists: {cherry_dir.exists()}")
    if cherry_dir.exists():
        gif_files = list(cherry_dir.glob("*.mp4"))
        print(f"   MP4 files: {len(gif_files)}")
    
    print(f"\n🍎 Pompon GIF directory: {pompon_dir}")
    print(f"   Exists: {pompon_dir.exists()}")
    if pompon_dir.exists():
        gif_files = list(pompon_dir.glob("*.mp4"))
        print(f"   MP4 files: {len(gif_files)}")
    
    assert cherry_dir.exists(), f"Cherry GIF directory not found: {cherry_dir}"
    assert pompon_dir.exists(), f"Pompon GIF directory not found: {pompon_dir}"
    
    print("\n✅ GIF directories exist!")
    return True


def test_enhanced_json_files():
    """Test that enhanced JSON files exist."""
    print("\n" + "=" * 60)
    print("Testing Enhanced JSON Files")
    print("=" * 60)
    
    cherry_json = project_root / "Cherry_GIF" / "GIF_descriptions_enhanced.json"
    pompon_json = project_root / "pompon_GIF" / "pompon_gif_description_enhanced.json"
    
    print(f"\n🍒 Cherry JSON: {cherry_json}")
    print(f"   Exists: {cherry_json.exists()}")
    
    print(f"\n🍎 Pompon JSON: {pompon_json}")
    print(f"   Exists: {pompon_json.exists()}")
    
    assert cherry_json.exists(), f"Cherry enhanced JSON not found: {cherry_json}"
    assert pompon_json.exists(), f"Pompon enhanced JSON not found: {pompon_json}"
    
    print("\n✅ Enhanced JSON files exist!")
    return True


def test_static_routes_registration():
    """Test that static routes can be registered."""
    print("\n" + "=" * 60)
    print("Testing Static Routes Registration")
    print("=" * 60)
    
    app = Flask(__name__)
    try:
        register_static_routes(app)
        print("\n✅ Static routes registered successfully!")
        
        # Check that routes exist
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        gif_routes = [r for r in routes if 'gif' in r.lower()]
        
        print(f"\n   Found {len(gif_routes)} GIF-related route(s):")
        for route in gif_routes:
            print(f"     - {route}")
        
        return True
    except Exception as e:
        print(f"\n❌ Error registering static routes: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GIF Directory Changes Verification")
    print("=" * 60)
    
    tests = [
        ("Character Configurations", test_character_configs),
        ("GIF Directory Existence", test_gif_directories_exist),
        ("Enhanced JSON Files", test_enhanced_json_files),
        ("Static Routes Registration", test_static_routes_registration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed, error in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
        if error:
            print(f"   Error: {error}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit(main())
