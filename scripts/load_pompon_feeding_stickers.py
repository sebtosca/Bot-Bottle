#!/usr/bin/env python3
"""Load Pompon feeding game stickers from Pompon_normand_feeding_game_logic_stickers/ into the database.

This script loads feeding game stickers for Pompon (character_id=00002).

Usage:
    python scripts/load_pompon_feeding_stickers.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_descriptions(stickers_dir: Path) -> Dict[str, str]:
    """Load sticker descriptions from cider_feeding_sticker_descriptions.json if present."""
    descriptions_file = stickers_dir / "cider_feeding_sticker_descriptions.json"
    if not descriptions_file.exists():
        return {}

    try:
        with open(descriptions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"⚠️  Warning: Could not load cider_feeding_sticker_descriptions.json: {exc}")
        return {}


def parse_metadata_from_filename(filename: str) -> Dict[str, Optional[str]]:
    """Parse accessory color, category, and fullness state from filename.

    Filenames follow: {color}_bouteille_affamee_{category}_{state}.webp
    Example: bleu_bouteille_affamee_papier_carton_pleine.webp
    """
    stem = filename.rsplit(".", 1)[0].lower()
    parts = stem.split("_")

    metadata = {
        "accessory_color": None,
        "category": None,
        "fullness_state": None,
    }

    if len(parts) < 5:
        return metadata

    color_fr = parts[0]
    category_fr = parts[3]
    state_fr = "_".join(parts[4:])  # handles multi-word states like deux_tiers_plein

    color_map = {
        "vert": "GREEN",
        "jaune": "YELLOW",
        "noir": "BLACK",
        "bleu": "BLUE",
    }

    category_map = {
        "verre": "glass",
        "plastique": "plastic",
        "non_recyclable": "non_recyclable",
        "papier_carton": "paper_cardboard",
    }

    state_map = {
        "pleine": "full",
        "deux_tiers_plein": "2/3",
        "un_tiers_plein": "1/3",
        "vide": "empty",
    }

    metadata["accessory_color"] = color_map.get(color_fr)
    metadata["category"] = category_map.get(category_fr)
    metadata["fullness_state"] = state_map.get(state_fr)
    return metadata


def load_pompon_feeding_stickers() -> int:
    print("=" * 60)
    print("Loading Pompon Feeding Game Stickers into Database")
    print("=" * 60)

    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as exc:
        print(f"❌ Database initialization failed: {exc}")
        return 1

    stickers_dir = Path(__file__).parent.parent / "Pompon_normand_feeding_game_logic_stickers"
    if not stickers_dir.exists():
        print(f"❌ Stickers directory not found: {stickers_dir}")
        return 1

    webp_files = list(stickers_dir.glob("*.webp"))
    if not webp_files:
        print(f"⚠️  No WebP files found in {stickers_dir}")
        return 0

    print(f"Found {len(webp_files)} Pompon feeding sticker file(s)")
    descriptions = load_descriptions(stickers_dir)
    if descriptions:
        print(f"✅ Loaded {len(descriptions)} description(s) from cider_feeding_sticker_descriptions.json\n")
    else:
        print("ℹ️  No cider_feeding_sticker_descriptions.json found. Using auto-generated descriptions.\n")

    session = get_session()
    created = 0
    updated = 0

    try:
        for sticker_file in webp_files:
            filename = sticker_file.name
            print(f"Processing: {filename}")

            meta = parse_metadata_from_filename(filename)
            accessory_color = meta["accessory_color"]
            category = meta["category"]
            fullness_state = meta["fullness_state"]

            # Build mood_tags to store contextual info (comma-separated)
            mood_tags_parts = []
            if accessory_color:
                mood_tags_parts.append(accessory_color)
            if category:
                mood_tags_parts.append(category)
            if fullness_state:
                mood_tags_parts.append(fullness_state)
            mood_tags_str = ",".join(mood_tags_parts) if mood_tags_parts else None

            description = descriptions.get(filename)
            if not description:
                desc_color = accessory_color or "unknown"
                desc_cat = category or "unknown"
                desc_state = fullness_state or "unknown"
                description = f"Pompon feeding game sticker ({desc_color}, {desc_cat}, {desc_state})"

            existing = session.query(Sticker).filter_by(filename=filename).first()

            # Character ID for Pompon
            character_id = "00002"

            if existing:
                existing.character_id = character_id
                existing.mood_tags = mood_tags_str
                existing.description = description
                existing.media_type = "sticker"
                existing.url = None  # Local file
                session.add(existing)
                updated += 1
                print(f"  ✅ Updated: character_id={character_id}, mood_tags={mood_tags_str}")
                print(f"     Description: {description[:60]}...")
            else:
                new_sticker = Sticker(
                    filename=filename,
                    character_id=character_id,
                    mood_tags=mood_tags_str,
                    description=description,
                    media_type="sticker",
                    url=None,
                    created_at=datetime.utcnow(),
                )
                session.add(new_sticker)
                created += 1
                print(f"  ✅ Created: character_id={character_id}, mood_tags={mood_tags_str}")
                print(f"     Description: {description[:60]}...")

        session.commit()

        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Created: {created}")
        print(f"  Updated: {updated}")
        print(f"  Total files processed: {len(webp_files)}")

        if created > 0 or updated > 0:
            print("\n✅ Pompon feeding game stickers loaded successfully!")
        return 0

    except Exception as exc:
        session.rollback()
        print(f"\n❌ Error loading Pompon feeding stickers: {exc}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(load_pompon_feeding_stickers())
