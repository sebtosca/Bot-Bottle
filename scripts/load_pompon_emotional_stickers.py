#!/usr/bin/env python3
"""Load Pompon emotional stickers from Pompom_normand_emotional_sticker/ into the database.

This script loads emotional stickers for Pompon (character_id=00002).

Usage:
    python scripts/load_pompon_emotional_stickers.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_pompon_emotional_stickers():
    """Load Pompon emotional stickers into database."""
    print("=" * 60)
    print("Loading Pompon Emotional Stickers into Database")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Get stickers directory and descriptions file
    project_root = Path(__file__).parent.parent
    stickers_dir = project_root / "Pompom_normand_emotional_sticker"
    descriptions_file = stickers_dir / "cider_emptional_sticker_descriptions.json"
    
    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1
    
    # Load descriptions
    descriptions = {}
    if descriptions_file.exists():
        try:
            with open(descriptions_file, "r", encoding="utf-8") as f:
                descriptions = json.load(f)
            print(f"✅ Loaded {len(descriptions)} description(s) from cider_emptional_sticker_descriptions.json\n")
        except Exception as e:
            print(f"⚠️  Warning: Could not load descriptions: {e}\n")
    else:
        print("ℹ️  No descriptions file found. Using auto-generated descriptions.\n")
    
    # Find all image files
    webp_files = list(stickers_dir.glob("*.webp"))
    png_files = list(stickers_dir.glob("*.png"))
    jpg_files = list(stickers_dir.glob("*.jpg")) + list(stickers_dir.glob("*.jpeg"))
    image_files = webp_files + png_files + jpg_files
    
    if not image_files:
        print(f"⚠️  No image files found in {stickers_dir}")
        return 0
    
    print(f"Found {len(image_files)} sticker file(s)\n")
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    
    try:
        for sticker_file in image_files:
            filename = sticker_file.name
            print(f"Processing: {filename}")
            
            # Check if sticker already exists
            existing = session.query(Sticker).filter_by(filename=filename).first()
            
            # Parse mood and hat color from filename (e.g. "happy_cider_green.webp")
            mood = None
            color = None
            name_lower = filename.lower()
            known_moods = ["happy", "sad", "angry", "scared", "shocked", "neutral"]
            for m in known_moods:
                if m in name_lower:
                    mood = m
                    break
            
            # Detect hat/bin color from filename suffix
            if "_green" in name_lower:
                color = "green"
            elif "_yellow" in name_lower:
                color = "yellow"
            elif "_blue" in name_lower:
                color = "blue"
            elif "_black" in name_lower:
                color = "black"
            
            # Encode both mood and color in mood_tags (e.g. "happy,green")
            tags = []
            if mood:
                tags.append(mood)
            if color:
                tags.append(color)
            mood_tags = ",".join(tags) if tags else None
            
            # Get description from JSON file or use default.
            # Descriptions file may use base filename without color (e.g. "happy_cider.webp").
            description = descriptions.get(filename)
            if not description:
                # Try base name without color suffix, e.g. "happy_cider.webp"
                parts = filename.split("_")
                if len(parts) >= 3:
                    base_name = "_".join(parts[:2]) + ".webp"
                    description = descriptions.get(base_name)
            if not description:
                description = f"Pompon emotional sticker ({mood or 'general'} mood)"
            
            # Character ID for Pompon
            character_id = "00002"
            
            if existing:
                # Update existing sticker
                existing.character_id = character_id
                existing.mood_tags = mood_tags
                existing.description = description
                existing.media_type = "sticker"
                existing.url = None
                session.add(existing)
                print(f"  ✅ Updated: character_id={character_id}, mood_tags={mood_tags}")
                print(f"     Description: {description[:60]}...")
                updated_count += 1
            else:
                # Create new sticker
                new_sticker = Sticker(
                    filename=filename,
                    character_id=character_id,
                    mood_tags=mood_tags,
                    description=description,
                    media_type="sticker",
                    url=None,
                    created_at=datetime.utcnow()
                )
                session.add(new_sticker)
                print(f"  ✅ Created: character_id={character_id}, mood_tags={mood_tags}")
                print(f"     Description: {description[:60]}...")
                loaded_count += 1
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Loaded: {loaded_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Total files processed: {len(image_files)}")
        
        if loaded_count > 0 or updated_count > 0:
            print("\n✅ Pompon emotional stickers loaded successfully!")
        
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
    exit(load_pompon_emotional_stickers())
