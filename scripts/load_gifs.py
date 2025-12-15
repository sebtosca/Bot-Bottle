"""Load local GIF/MP4 files from the GIF directory into the database.

This script scans the GIF directory for all MP4/GIF files and loads them
into the database. It uses:
- gifs.json (optional) for mood_tags metadata
- GIF/GIF_descriptions.json (optional) for descriptions

All files in the GIF directory will be loaded, regardless of whether
they're listed in gifs.json.

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
    
    # Get gifs.json file, GIF_descriptions.json, and GIF directory
    project_root = Path(__file__).parent.parent
    gifs_file = project_root / "gifs.json"
    gif_descriptions_file = project_root / "GIF" / "GIF_descriptions.json"
    gifs_dir = project_root / "GIF"
    
    if not gifs_dir.exists():
        print(f"❌ GIF directory not found: {gifs_dir}")
        print("   Create this directory and place your MP4/GIF files in it.")
        return 1
    
    # Load GIFs metadata from JSON file (optional - for mood_tags)
    gifs_metadata = {}
    if gifs_file.exists():
        try:
            with open(gifs_file, "r", encoding="utf-8") as f:
                gifs_data = json.load(f)
            # Build a mapping from filename to metadata
            for gif_name, gif_info in gifs_data.items():
                if isinstance(gif_info, dict):
                    filename = gif_info.get("filename")
                    if filename:
                        gifs_metadata[filename] = gif_info
            if gifs_metadata:
                print(f"✅ Loaded metadata for {len(gifs_metadata)} GIF(s) from gifs.json")
        except Exception as e:
            print(f"⚠️  Warning: Could not read gifs.json: {e}")
            print("   Continuing without gifs.json metadata...")
    else:
        print("ℹ️  gifs.json not found. Will load all GIFs from directory without mood_tags.")
    
    print()
    
    # Load descriptions from GIF_descriptions.json if it exists
    descriptions_dict = {}
    if gif_descriptions_file.exists():
        try:
            with open(gif_descriptions_file, "r", encoding="utf-8") as f:
                descriptions_dict = json.load(f)
            print(f"✅ Loaded {len(descriptions_dict)} description(s) from GIF_descriptions.json")
        except Exception as e:
            print(f"⚠️  Warning: Could not read GIF_descriptions.json: {e}")
            print("   Continuing without descriptions file...")
    else:
        print("ℹ️  GIF_descriptions.json not found. Will use descriptions from gifs.json if available.")
    
    print()
    
    # Scan GIF directory for all MP4/GIF files
    gif_files = list(gifs_dir.glob("*.mp4")) + list(gifs_dir.glob("*.gif"))
    # Exclude JSON files
    gif_files = [f for f in gif_files if f.suffix.lower() in {".mp4", ".gif"}]
    
    if not gif_files:
        print(f"⚠️  No GIF/MP4 files found in {gifs_dir}")
        print("   Place your MP4/GIF files in the GIF directory.")
        return 0
    
    print(f"Found {len(gif_files)} GIF/MP4 file(s) in directory\n")
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    error_count = 0
    
    # Collect all valid filenames from directory
    valid_filenames = {f.name for f in gif_files}
    
    # Clean up old GIF records that don't have matching files
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
        for gif_path in sorted(gif_files):
            filename = gif_path.name
            print(f"Processing: {filename}")

            # Get metadata from gifs.json if available
            gif_metadata = gifs_metadata.get(filename, {})
            mood_tags = gif_metadata.get("mood_tags", "")
            
            # Get description: prefer GIF_descriptions.json, fallback to gifs.json, then default
            description = None
            if filename in descriptions_dict:
                description = descriptions_dict[filename]
                print(f"  📝 Using description from GIF_descriptions.json")
            elif gif_metadata.get("description"):
                description = gif_metadata.get("description")
            else:
                description = f"GIF: {filename}"
            
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
                if mood_tags:
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
                if mood_tags:
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
        print(f"  Total files processed: {len(gif_files)}")
        
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

