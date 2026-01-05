#!/usr/bin/env python3
"""Load Cherry emotional stickers from stickers/ into the database.

This script loads emotional stickers for Cherry (character_id=00001),
including the new emotion+color variants whose hat color indicates
which bin/color the user should feed.

Usage:
    python scripts/load_cherry_emotional_stickers.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_cherry_emotional_stickers() -> int:
    """Load Cherry emotional stickers into database."""
    print("=" * 60)
    print("Loading Cherry Emotional Stickers into Database")
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
    stickers_dir = project_root / "stickers"
    descriptions_file = stickers_dir / "descriptions.json"

    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1

    # Load descriptions
    descriptions = {}
    if descriptions_file.exists():
        try:
            with open(descriptions_file, "r", encoding="utf-8") as f:
                descriptions = json.load(f)
            print(f"✅ Loaded {len(descriptions)} description(s) from descriptions.json\n")
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

            # Only process Cherry emotional stickers (e.g. happy_cherry_green.webp)
            if "cherry" not in filename.lower():
                continue

            print(f"Processing: {filename}")

            # Check if sticker already exists
            existing = session.query(Sticker).filter_by(filename=filename).first()

            # Parse mood and hat color from filename (e.g. "happy_cherry_green.webp")
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

            # Get description from JSON file or use default
            description = descriptions.get(filename)
            if not description:
                description = f"Cherry emotional sticker ({mood or 'general'} mood)"

            # Character ID for Cherry
            character_id = "00001"

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
                    created_at=datetime.utcnow(),
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
            print("\n✅ Cherry emotional stickers loaded successfully!")

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
    raise SystemExit(load_cherry_emotional_stickers())

