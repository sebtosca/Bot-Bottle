#!/usr/bin/env python3
"""Check if stickers meet WhatsApp Cloud API requirements."""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌ PIL/Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)

# WhatsApp Cloud API sticker requirements
REQUIREMENTS = {
    "format": "WEBP",
    "dimensions": (512, 512),  # width x height
    "max_size_static": 100 * 1024,  # 100 KB
    "max_size_animated": 500 * 1024,  # 500 KB
    "background": "transparent"
}

def check_sticker(file_path: Path):
    """Check if a sticker file meets WhatsApp requirements."""
    print(f"\n{'='*60}")
    print(f"Checking: {file_path.name}")
    print(f"{'='*60}")
    
    # Check file exists
    if not file_path.exists():
        print("❌ File does not exist")
        return False
    
    # Check file size
    file_size = file_path.stat().st_size
    print(f"File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    
    if file_size > REQUIREMENTS["max_size_static"]:
        print(f"❌ File too large: {file_size/1024:.1f} KB > {REQUIREMENTS['max_size_static']/1024} KB (max for static)")
        return False
    else:
        print(f"✅ File size OK")
    
    # Check image properties
    try:
        img = Image.open(file_path)
        print(f"Format: {img.format}")
        print(f"Dimensions: {img.size[0]}x{img.size[1]} pixels")
        print(f"Mode: {img.mode}")
        
        # Check format
        if img.format != "WEBP":
            print(f"❌ Wrong format: {img.format} (required: WEBP)")
            if file_path.suffix.lower() == ".webp":
                print(f"   ⚠️  File has .webp extension but is actually {img.format}")
            return False
        else:
            print(f"✅ Format OK (WEBP)")
        
        # Check dimensions
        required_w, required_h = REQUIREMENTS["dimensions"]
        actual_w, actual_h = img.size
        
        if actual_w != required_w or actual_h != required_h:
            print(f"❌ Wrong dimensions: {actual_w}x{actual_h} (required: {required_w}x{required_h})")
            return False
        else:
            print(f"✅ Dimensions OK ({required_w}x{required_h})")
        
        # Check transparency (RGBA mode indicates transparency)
        if img.mode != "RGBA":
            print(f"⚠️  Mode is {img.mode} (RGBA preferred for transparency)")
        else:
            print(f"✅ Has transparency (RGBA)")
        
        print(f"\n✅ {file_path.name} MEETS ALL REQUIREMENTS")
        return True
        
    except Exception as e:
        print(f"❌ Error reading image: {e}")
        return False


def main():
    """Check all stickers in the stickers directory."""
    stickers_dir = Path(__file__).parent / "stickers"
    
    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1
    
    print("=" * 60)
    print("WhatsApp Cloud API Sticker Requirements Check")
    print("=" * 60)
    print("\nRequirements:")
    print(f"  Format: {REQUIREMENTS['format']}")
    print(f"  Dimensions: {REQUIREMENTS['dimensions'][0]}x{REQUIREMENTS['dimensions'][1]} pixels")
    print(f"  Max size (static): {REQUIREMENTS['max_size_static']/1024} KB")
    print(f"  Max size (animated): {REQUIREMENTS['max_size_animated']/1024} KB")
    print(f"  Background: {REQUIREMENTS['background']}")
    
    # Find all sticker files
    sticker_files = list(stickers_dir.glob("*.webp")) + list(stickers_dir.glob("*.png"))
    
    if not sticker_files:
        print(f"\n❌ No sticker files found in {stickers_dir}")
        return 1
    
    print(f"\nFound {len(sticker_files)} sticker file(s)")
    
    results = []
    for sticker_file in sorted(sticker_files):
        result = check_sticker(sticker_file)
        results.append((sticker_file.name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    valid_count = sum(1 for _, valid in results if valid)
    total_count = len(results)
    
    for name, valid in results:
        status = "✅ VALID" if valid else "❌ INVALID"
        print(f"{status}: {name}")
    
    print(f"\nValid stickers: {valid_count}/{total_count}")
    
    if valid_count == 0:
        print("\n⚠️  No valid stickers found!")
        print("   You need to convert/resize your stickers to meet WhatsApp requirements:")
        print("   - Format: WEBP")
        print("   - Dimensions: 512x512 pixels")
        print("   - Size: ≤100 KB")
        return 1
    elif valid_count < total_count:
        print(f"\n⚠️  Only {valid_count} sticker(s) are valid")
        print("   Consider fixing the invalid ones")
    
    return 0


if __name__ == "__main__":
    exit(main())

