#!/usr/bin/env python3
"""Fix stickers to meet WhatsApp Cloud API requirements."""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌ PIL/Pillow not installed. Install with: pip install Pillow")
    sys.exit(1)

# WhatsApp requirements
TARGET_SIZE = (512, 512)  # width x height
MAX_SIZE_KB = 100
QUALITY = 85  # WebP quality (0-100, lower = smaller file)

def remove_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Remove white/light background and make it transparent.
    
    Args:
        img: PIL Image in RGB or RGBA mode
        threshold: Brightness threshold (0-255). Pixels brighter than this become transparent.
                   Default 240 works well for white/light backgrounds.
    
    Returns:
        Image with transparent background (RGBA mode)
    """
    # Ensure we have RGBA mode
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    # Get image data
    data = img.getdata()
    new_data = []
    
    for item in data:
        # If pixel is white/light (brightness > threshold), make it transparent
        # Calculate brightness: (R + G + B) / 3
        if len(item) == 4:  # RGBA
            r, g, b, a = item
        else:  # RGB (shouldn't happen, but handle it)
            r, g, b = item[:3]
            a = 255
        
        brightness = (r + g + b) / 3
        
        if brightness >= threshold:
            # Make transparent
            new_data.append((r, g, b, 0))
        else:
            # Keep original (preserve existing alpha if any)
            new_data.append((r, g, b, a))
    
    img.putdata(new_data)
    return img

def fix_sticker(input_path: Path, output_path: Path = None, remove_bg: bool = False):
    """Resize and convert sticker to meet WhatsApp requirements."""
    if output_path is None:
        output_path = input_path.with_suffix('.webp')
    
    print(f"\nProcessing: {input_path.name}")
    
    try:
        # Open image
        img = Image.open(input_path)
        print(f"  Original: {img.size[0]}x{img.size[1]}, {img.format}, {img.mode}")
        
        # Convert to RGBA if needed (for transparency)
        if img.mode != "RGBA":
            if img.mode == "RGB":
                # Add alpha channel
                img = img.convert("RGBA")
            else:
                img = img.convert("RGBA")
            print(f"  Converted to RGBA for transparency")
        
        # Remove background if requested (makes white/light backgrounds transparent)
        if remove_bg:
            # Check if image already has transparency by sampling alpha channel
            has_transparency = False
            if img.mode == "RGBA":
                # Sample a few pixels to check for transparency
                sample_pixels = [
                    img.getpixel((0, 0)),
                    img.getpixel((img.width-1, 0)),
                    img.getpixel((0, img.height-1)),
                    img.getpixel((img.width-1, img.height-1))
                ]
                has_transparency = any(len(p) == 4 and p[3] < 255 for p in sample_pixels)
            
            if not has_transparency:
                # No existing transparency, remove white/light background
                img = remove_background(img, threshold=240)
                print(f"  Removed white/light background (made transparent)")
            else:
                print(f"  Preserving existing transparency")
        
        # Resize to 512x512 (maintain aspect ratio, then crop/pad)
        img_resized = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
        print(f"  Resized to: {img_resized.size[0]}x{img_resized.size[1]}")
        
        # Save as WebP with compression
        # Try different quality levels to get under 100KB
        quality = QUALITY
        saved = False
        
        for attempt in range(5):
            img_resized.save(output_path, "WEBP", quality=quality, method=6)
            file_size = output_path.stat().st_size
            size_kb = file_size / 1024
            
            print(f"  Quality {quality}: {size_kb:.1f} KB", end="")
            
            if file_size <= MAX_SIZE_KB * 1024:
                print(" ✅")
                saved = True
                break
            else:
                print(f" (too large, trying lower quality)")
                quality -= 10
        
        if not saved:
            # Last resort: try very low quality
            quality = 50
            img_resized.save(output_path, "WEBP", quality=quality, method=6)
            file_size = output_path.stat().st_size
            size_kb = file_size / 1024
            print(f"  Final attempt (quality {quality}): {size_kb:.1f} KB", end="")
            
            if file_size <= MAX_SIZE_KB * 1024:
                print(" ✅")
                saved = True
            else:
                print(f" ❌ Still too large")
        
        if saved:
            print(f"  ✅ Saved: {output_path.name} ({size_kb:.1f} KB)")
            return True
        else:
            print(f"  ❌ Could not compress below {MAX_SIZE_KB} KB")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fix all stickers in the stickers directory."""
    stickers_dir = Path(__file__).parent / "sorting_logic_stickers"
    
    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1
    
    # Find all image files (PNG, WebP, JPG, JPEG)
    png_files = list(stickers_dir.glob("*.png"))
    webp_files = list(stickers_dir.glob("*.webp"))
    jpg_files = list(stickers_dir.glob("*.jpg")) + list(stickers_dir.glob("*.jpeg"))
    image_files = png_files + webp_files + jpg_files
    
    if not image_files:
        print(f"❌ No image files found in {stickers_dir}")
        print("   Supported formats: PNG, WebP, JPG, JPEG")
        return 1
    
    print("=" * 60)
    print("Fixing Stickers for WhatsApp Cloud API")
    print("=" * 60)
    print(f"\nTarget: 512x512 pixels, WEBP format, ≤{MAX_SIZE_KB} KB")
    print(f"Found {len(image_files)} image file(s)")
    if png_files:
        print(f"  PNG: {len(png_files)}")
    if webp_files:
        print(f"  WebP: {len(webp_files)}")
    if jpg_files:
        print(f"  JPG/JPEG: {len(jpg_files)}")
    
    # Ask for confirmation
    print("\nThis will:")
    print("  1. Resize images to 512x512 pixels")
    print("  2. Convert PNG/JPG/JPEG to WEBP format")
    print("  3. Compress to ≤100 KB")
    print("  4. Save as .webp files (preserving original backgrounds)")
    
    response = input("\nProceed? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return 0
    
    results = []
    for img_file in sorted(image_files):
        # Create output filename (always .webp)
        output_file = img_file.with_suffix('.webp')
        
        # Skip if already WebP and might be valid
        if img_file.suffix.lower() == '.webp':
            # Check if it might already be valid
            try:
                img = Image.open(img_file)
                file_size = img_file.stat().st_size
                if (img.size == TARGET_SIZE and 
                    img.format == "WEBP" and 
                    file_size <= MAX_SIZE_KB * 1024):
                    print(f"\n⏭️  Skipping {img_file.name} (already valid)")
                    results.append((img_file.name, True))
                    continue
            except:
                pass
        
        result = fix_sticker(img_file, output_file, remove_bg=False)
        results.append((output_file.name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nFixed: {success_count}/{total_count}")
    
    if success_count > 0:
        print("\n✅ Stickers fixed! You can now test sending them.")
        print("   Run: python check_sticker_requirements.py")
        print("   Then: python test_send_sticker_simple.py +33684950535")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit(main())

