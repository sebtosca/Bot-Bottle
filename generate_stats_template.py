#!/usr/bin/env python3
"""Generate and preview the stats card template.

This script generates a base template image that will be reused,
with placeholder data so you can review the design.

Usage:
    python generate_stats_template.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from stats_visualizer import generate_base_template, overlay_dynamic_data
from PIL import Image

def main():
    """Generate and save template for review."""
    print("=" * 60)
    print("Generating Stats Card Template")
    print("=" * 60)
    print()
    
    # Generate base template
    print("1. Generating base template...")
    template = generate_base_template()
    
    # Save template
    template_path = Path(__file__).parent / "stats_template_base.png"
    template.save(template_path)
    print(f"   ✅ Template saved to: {template_path}")
    print()
    
    # Generate sample with dynamic data overlay
    print("2. Generating sample with dynamic data overlay...")
    sample_stats = {
        'current_title': 'Novice',
        'total_points': 150,
        'total_money_saved': 2.50,
        'total_co2_saved': 1.25,
        'character_count': 2,
        'active_characters': 2,
        'returned_characters': 0,
        'characters': [
            {'name': 'Cherry', 'product_id': '00001', 'points_earned': 100, 
             'money_saved': 1.20, 'co2_saved': 0.60, 'fullness': 75.0},
            {'name': 'Pompon', 'product_id': '00002', 'points_earned': 50, 
             'money_saved': 1.30, 'co2_saved': 0.65, 'fullness': 34.0}
        ]
    }
    
    sample_image = overlay_dynamic_data(template.copy(), sample_stats)
    sample_path = Path(__file__).parent / "stats_template_sample.png"
    sample_image.save(sample_path)
    print(f"   ✅ Sample saved to: {sample_path}")
    print()
    
    print("=" * 60)
    print("✅ Template Generation Complete!")
    print("=" * 60)
    print()
    print("Review the generated images:")
    print(f"  - Base template: {template_path}")
    print(f"  - Sample with data: {sample_path}")
    print()
    print("If you're happy with the design, the template will be cached")
    print("and reused with dynamic data overlays for each user.")

if __name__ == "__main__":
    main()
