#!/usr/bin/env python3
"""Load Pompon GIFs from pompon_GIF/ into the database.

This script loads GIFs for Pompon (character_id=00002).

Usage:
    python scripts/load_pompon_gifs.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_pompon_gifs():
    """Load Pompon GIFs into database."""
    print("=" * 60)
    print("Loading Pompon GIFs into Database")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Get Pompon GIF directory and descriptions file
    project_root = Path(__file__).parent.parent
    gifs_dir = project_root / "pompon_GIF"
    descriptions_file = gifs_dir / "pompon_gif_description.json"
    
    if not gifs_dir.exists():
        print(f"❌ GIF directory not found: {gifs_dir}")
        return 1
    
    # Load descriptions
    descriptions = {}
    if descriptions_file.exists():
        try:
            with open(descriptions_file, "r", encoding="utf-8") as f:
                descriptions = json.load(f)
            print(f"✅ Loaded {len(descriptions)} description(s) from pompon_gif_description.json\n")
        except Exception as e:
            print(f"⚠️  Warning: Could not load descriptions: {e}\n")
    else:
        print("ℹ️  No descriptions file found. Using auto-generated descriptions.\n")
    
    # Find all MP4/GIF files
    mp4_files = list(gifs_dir.glob("*.mp4"))
    gif_files = list(gifs_dir.glob("*.gif"))
    gif_files_list = mp4_files + gif_files
    
    if not gif_files_list:
        print(f"⚠️  No GIF/MP4 files found in {gifs_dir}")
        return 0
    
    print(f"Found {len(gif_files_list)} GIF/MP4 file(s)\n")
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    
    try:
        for gif_file in sorted(gif_files_list):
            filename = gif_file.name
            print(f"Processing: {filename}")
            
            # Check if GIF already exists
            existing = session.query(Sticker).filter_by(
                filename=filename,
                media_type="gif"
            ).first()
            
            # Get description from JSON file or use default
            description = descriptions.get(filename)
            if not description:
                description = f"Pompon GIF: {filename}"
            
            # Basic WhatsApp-related checks: extension and size
            if gif_file.suffix.lower() not in {".mp4", ".gif"}:
                print(f"  ⚠️  Unexpected extension for GIF media: {gif_file.suffix}")
            size_kb = gif_file.stat().st_size / 1024
            if size_kb > 1500:
                print(f"  ⚠️  File is larger than ~1.5MB ({size_kb:.1f} KB). WhatsApp may reject it.")
            
            # Character ID for Pompon
            character_id = "00002"
            
            if existing:
                # Update existing GIF
                existing.character_id = character_id
                existing.description = description
                existing.media_type = "gif"
                existing.url = None
                session.add(existing)
                print(f"  ✅ Updated: character_id={character_id}")
                print(f"     Description: {description[:60]}...")
                updated_count += 1
            else:
                # Create new GIF
                new_gif = Sticker(
                    filename=filename,
                    character_id=character_id,
                    mood_tags=None,  # Can be set later if needed
                    description=description,
                    media_type="gif",
                    url=None,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_gif)
                print(f"  ✅ Created: character_id={character_id}")
                print(f"     Description: {description[:60]}...")
                loaded_count += 1
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Loaded: {loaded_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Total files processed: {len(gif_files_list)}")
        
        if loaded_count > 0 or updated_count > 0:
            print("\n✅ Pompon GIFs loaded successfully!")
        
        return 0
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading Pompon GIFs: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(load_pompon_gifs())
