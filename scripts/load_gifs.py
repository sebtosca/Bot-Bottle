"""Load local GIF/MP4 metadata from gifs.json into the database.

This script reads GIF entries from gifs.json and loads them
into the database with mood metadata, assuming each GIF is a
local file served via the /gifs/<filename> Flask route.

Usage:
    python scripts/load_gifs.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_gifs():
    """Load GIFs from gifs.json into database."""
    print("=" * 60)
    print("Loading GIFs into Database")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Get gifs.json file and GIF directory
    project_root = Path(__file__).parent.parent
    gifs_file = project_root / "gifs.json"
    gifs_dir = project_root / "GIF"
    
    if not gifs_file.exists():
        print(f"❌ gifs.json file not found: {gifs_file}")
        print("\nCreate gifs.json in the project root with the following format:")
        print("""
{
  "gif_name_1": {
    "filename": "my_clip.mp4",
    "mood_tags": "happy,excited",
    "description": "Description of the GIF"
  },
  "gif_name_2": {
    "filename": "another_clip.mp4",
    "mood_tags": "sad,lonely",
    "description": "Another GIF description"
  }
}
""")
        return 1
    
    # Load GIFs from JSON file
    try:
        with open(gifs_file, "r", encoding="utf-8") as f:
            gifs_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading gifs.json: {e}")
        return 1
    
    if not gifs_data:
        print("⚠️  gifs.json is empty")
        return 0
    
    print(f"Found {len(gifs_data)} GIF entry/entries in gifs.json\n")
    if not gifs_dir.exists():
        print(f"❌ GIF directory not found: {gifs_dir}")
        print("   Create this directory and place your MP4/GIF files in it.")
        return 1
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    error_count = 0
    
    # Collect all valid filenames from gifs.json
    valid_filenames = set()
    for gif_name, gif_info in gifs_data.items():
        if isinstance(gif_info, dict):
            filename = gif_info.get("filename")
            if filename:
                valid_filenames.add(filename)
    
    # Clean up old GIF records that don't have matching files
    # (e.g., old .gif files that were converted to .mp4)
    all_gifs = session.query(Sticker).filter(Sticker.media_type == "gif").all()
    deleted_count = 0
    for old_gif in all_gifs:
        if old_gif.filename and old_gif.filename not in valid_filenames:
            # Check if file exists
            old_path = gifs_dir / old_gif.filename
            if not old_path.exists():
                print(f"  🗑️  Deleting orphaned GIF record: {old_gif.filename}")
                session.delete(old_gif)
                deleted_count += 1
    if deleted_count > 0:
        print(f"  Cleaned up {deleted_count} orphaned GIF record(s)\n")
    
    try:
        for gif_name, gif_info in gifs_data.items():
            print(f"Processing: {gif_name}")
            
            # Validate required fields
            if not isinstance(gif_info, dict):
                print(f"  ❌ Invalid entry format (must be object)")
                error_count += 1
                continue
            
            filename = gif_info.get("filename")
            if not filename:
                print(f"  ❌ Missing 'filename' field")
                error_count += 1
                continue
            
            mood_tags = gif_info.get("mood_tags", "")
            description = gif_info.get("description", f"GIF: {gif_name}")
            
            # Validate that the file exists in the GIF directory
            gif_path = gifs_dir / filename
            if not gif_path.exists():
                print(f"  ❌ File not found in GIF directory: {gif_path}")
                error_count += 1
                continue

            # Basic WhatsApp-related checks: extension and size.
            # WhatsApp \"GIFs\" should be short MP4 clips (< 6s, no audio),
            # recommended under ~1.5MB. Here we only warn about extension/size.
            if gif_path.suffix.lower() not in {".mp4", ".gif"}:
                print(f"  ⚠️  Unexpected extension for GIF media: {gif_path.suffix}")
            size_kb = gif_path.stat().st_size / 1024
            if size_kb > 1500:
                print(f"  ⚠️  File is larger than ~1.5MB ({size_kb:.1f} KB). WhatsApp may reject it.")
            
            # Check if GIF already exists (by filename)
            existing = session.query(Sticker).filter_by(
                filename=filename,
                media_type="gif"
            ).first()
            
            if existing:
                # Update existing GIF
                existing.mood_tags = mood_tags
                existing.description = description
                # Ensure filename is kept in sync and legacy URL cleared
                existing.filename = filename
                existing.url = None
                session.add(existing)
                print(f"  ✅ Updated: {filename}")
                print(f"     mood_tags={mood_tags}")
                print(f"     Description: {description[:60]}...")
                updated_count += 1
            else:
                # Create new GIF entry backed by a local file
                new_gif = Sticker(
                    filename=filename,
                    mood_tags=mood_tags,
                    description=description,
                    media_type="gif",
                    url=None,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_gif)
                print(f"  ✅ Created: {filename}")
                print(f"     mood_tags={mood_tags}")
                print(f"     Description: {description[:60]}...")
                loaded_count += 1
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"  Loaded: {loaded_count}")
        print(f"  Updated: {updated_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total entries processed: {len(gifs_data)}")
        
        if loaded_count > 0 or updated_count > 0:
            print("\n✅ GIFs loaded successfully!")
            print("\nTo manually update mood tags, edit gifs.json and run this script again,")
            print("or edit the database directly.")
        
        return 0
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading GIFs: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(load_gifs())

