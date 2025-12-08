"""Load sticker files from stickers/ directory into database.

This script scans the stickers/ directory for .webp files and loads them
into the database with mood metadata.

Usage:
    python scripts/load_stickers.py
"""

import sys
import json
from pathlib import Path
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker
from datetime import datetime


def load_descriptions(stickers_dir: Path) -> dict[str, str]:
    """Load sticker descriptions from descriptions.json file.
    
    Args:
        stickers_dir: Path to stickers directory
    
    Returns:
        Dictionary mapping filename -> description
    """
    descriptions_file = stickers_dir / "descriptions.json"
    
    if not descriptions_file.exists():
        return {}
    
    try:
        with open(descriptions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Warning: Could not load descriptions.json: {e}")
        return {}


def parse_mood_from_filename(filename: str) -> list[str]:
    """Parse mood tags from filename.
    
    Examples:
        happy_cherry.webp -> ["happy"]
        excited_sparkles.webp -> ["excited"]
        neutral_cherry.webp -> ["neutral"]
        happy_excited_cherry.webp -> ["happy", "excited"]
        happy_cherry.png -> ["happy"]
    
    Args:
        filename: Sticker filename (e.g., "happy_cherry.webp" or "happy_cherry.png")
    
    Returns:
        List of mood tags found in filename.
    """
    # Remove file extension (.webp, .png, .jpg, etc.)
    name = filename.rsplit('.', 1)[0].lower() if '.' in filename else filename.lower()
    
    # Known moods from state_logic.py and additional moods from stickers
    known_moods = ["neutral", "happy", "content", "playful", "excited", "curious", 
                   "sad", "angry", "scared", "shocked", "frightened", "surprised"]
    
    found_moods = []
    for mood in known_moods:
        if mood in name:
            found_moods.append(mood)
    
    return found_moods


def load_stickers():
    """Scan stickers/ directory and load into database."""
    print("=" * 60)
    print("Loading Stickers into Database")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Get stickers directory
    stickers_dir = Path(__file__).parent.parent / "stickers"
    
    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1
    
    # Find all image files (prefer WebP for WhatsApp Cloud API)
    # WhatsApp Cloud API supports WebP, PNG, JPEG
    webp_files = list(stickers_dir.glob("*.webp"))
    png_files = list(stickers_dir.glob("*.png"))
    jpg_files = list(stickers_dir.glob("*.jpg")) + list(stickers_dir.glob("*.jpeg"))
    
    # Combine all image files (prioritize WebP for better compression)
    image_files = webp_files + png_files + jpg_files
    
    if not image_files:
        print(f"⚠️  No image files found in {stickers_dir}")
        print("\nPlace your sticker files (.webp, .png, .jpg, or .jpeg) in the stickers/ directory.")
        print("Note: WhatsApp Cloud API supports all these formats. WebP is preferred for better compression.")
        return 0
    
    print(f"Found {len(image_files)} sticker file(s)")
    print(f"  WebP: {len(webp_files)} (preferred)")
    print(f"  PNG: {len(png_files)}")
    print(f"  JPEG: {len(jpg_files)}")
    print()
    
    # Load descriptions from JSON file
    descriptions = load_descriptions(stickers_dir)
    if descriptions:
        print(f"✅ Loaded {len(descriptions)} description(s) from descriptions.json\n")
    else:
        print("ℹ️  No descriptions.json found. Using auto-generated descriptions.\n")
        print("   Create stickers/descriptions.json to add custom descriptions.\n")
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    skipped_count = 0
    
    try:
        for sticker_file in image_files:
            filename = sticker_file.name
            print(f"Processing: {filename}")
            
            # Check if sticker already exists
            existing = session.query(Sticker).filter_by(filename=filename).first()
            
            # Parse mood from filename
            mood_tags = parse_mood_from_filename(filename)
            mood_tags_str = ",".join(mood_tags) if mood_tags else None
            
            # Get description from JSON file or use default
            description = descriptions.get(filename)
            if not description:
                description = f"Sticker for {mood_tags_str or 'general'} mood"
            
            if existing:
                # Update existing sticker
                existing.mood_tags = mood_tags_str
                existing.description = description
                existing.media_type = "sticker"  # Ensure it's marked as sticker
                existing.url = None  # Local files don't have URLs
                session.add(existing)
                print(f"  ✅ Updated: mood_tags={mood_tags_str}")
                print(f"     Description: {description[:60]}...")
                updated_count += 1
            else:
                # Create new sticker
                new_sticker = Sticker(
                    filename=filename,
                    mood_tags=mood_tags_str,
                    description=description,
                    media_type="sticker",
                    url=None,  # Local files don't have URLs
                    created_at=datetime.utcnow()
                )
                session.add(new_sticker)
                print(f"  ✅ Created: mood_tags={mood_tags_str}")
                print(f"     Description: {description[:60]}...")
                loaded_count += 1
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Loaded: {loaded_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Total files processed: {len(image_files)}")
        
        if loaded_count > 0 or updated_count > 0:
            print("\n✅ Stickers loaded successfully!")
            print("\nTo manually set mood tags, edit the database or use:")
            print("  python -c \"from db.db import *; s = get_session(); st = s.query(Sticker).filter_by(filename='your_file.webp').first(); st.mood_tags = 'happy,excited'; s.commit()\"")
        
        return 0
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading stickers: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(load_stickers())

