"""Load local GIF/MP4 files from the money_GIF directory into the database.

This script scans the money_GIF directory for all MP4/GIF files and loads them
into the database. It uses:
- money_gid_descriptions.json for descriptions
- Tags all money GIFs with "empty,deposit,money" mood tags

All files in the money_GIF directory will be loaded with special mood tags
to identify them as deposit incentive GIFs.

Usage:
    python scripts/load_money_gifs.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker


def load_money_gifs():
    """Load money GIFs from money_GIF directory into database."""
    print("=" * 60)
    print("Loading Money GIFs into Database")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("✅ Database initialized\n")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1
    
    # Get money_gid_descriptions.json and money_GIF directory
    project_root = Path(__file__).parent.parent
    money_descriptions_file = project_root / "money_GIF" / "money_gid_descriptions.json"
    money_gifs_dir = project_root / "money_GIF"
    
    if not money_gifs_dir.exists():
        print(f"❌ money_GIF directory not found: {money_gifs_dir}")
        print("   Create this directory and place your MP4/GIF files in it.")
        return 1
    
    # Load descriptions from money_gid_descriptions.json if it exists
    descriptions_dict = {}
    if money_descriptions_file.exists():
        try:
            with open(money_descriptions_file, "r", encoding="utf-8") as f:
                descriptions_dict = json.load(f)
            print(f"✅ Loaded {len(descriptions_dict)} description(s) from money_gid_descriptions.json")
        except Exception as e:
            print(f"⚠️  Warning: Could not read money_gid_descriptions.json: {e}")
            print("   Continuing without descriptions file...")
    else:
        print("ℹ️  money_gid_descriptions.json not found. Will use default descriptions.")
    
    print()
    
    # Scan money_GIF directory for all MP4/GIF files
    gif_files = list(money_gifs_dir.glob("*.mp4")) + list(money_gifs_dir.glob("*.gif"))
    # Exclude JSON files
    gif_files = [f for f in gif_files if f.suffix.lower() in {".mp4", ".gif"}]
    
    if not gif_files:
        print(f"⚠️  No GIF/MP4 files found in {money_gifs_dir}")
        print("   Place your MP4/GIF files in the money_GIF directory.")
        return 0
    
    print(f"Found {len(gif_files)} GIF/MP4 file(s) in directory\n")
    
    session = get_session()
    loaded_count = 0
    updated_count = 0
    error_count = 0
    
    # Collect all valid filenames from directory
    valid_filenames = {f.name for f in gif_files}
    
    # Clean up old money GIF records that don't have matching files
    # Money GIFs are identified by mood_tags containing "empty" or "deposit" or "money"
    all_gifs = session.query(Sticker).filter(Sticker.media_type == "gif").all()
    deleted_count = 0
    for old_gif in all_gifs:
        if old_gif.mood_tags and any(tag in old_gif.mood_tags.lower() for tag in ["empty", "deposit", "money"]):
            # This is a money GIF, check if file still exists
            if old_gif.filename and old_gif.filename not in valid_filenames:
                old_path = money_gifs_dir / old_gif.filename
                if not old_path.exists():
                    print(f"  🗑️  Deleting orphaned money GIF record: {old_gif.filename}")
                    session.delete(old_gif)
                    deleted_count += 1
    if deleted_count > 0:
        print(f"  Cleaned up {deleted_count} orphaned money GIF record(s)\n")
    
    try:
        for gif_path in sorted(gif_files):
            filename = gif_path.name
            print(f"Processing: {filename}")

            # Money GIFs always get these mood tags
            mood_tags = "empty,deposit,money"
            
            # Get description from money_gid_descriptions.json if available
            description = None
            if filename in descriptions_dict:
                description = descriptions_dict[filename]
                print(f"  📝 Using description from money_gid_descriptions.json")
            else:
                description = f"Money GIF: {filename}"
            
            # Basic WhatsApp-related checks: extension and size.
            # WhatsApp "GIFs" should be short MP4 clips (< 6s, no audio),
            # recommended under ~1.5MB. Here we only warn about extension/size.
            if gif_path.suffix.lower() not in {".mp4", ".gif"}:
                print(f"  ⚠️  Unexpected extension for GIF media: {gif_path.suffix}")
            size_kb = gif_path.stat().st_size / 1024
            if size_kb > 1500:
                print(f"  ⚠️  File is larger than ~1.5MB ({size_kb:.1f} KB). WhatsApp may reject it.")
            
            # Check if GIF already exists (by filename and mood tags)
            existing = session.query(Sticker).filter_by(
                filename=filename,
                media_type="gif"
            ).first()
            
            # Also check if it's a money GIF by mood tags
            if existing and existing.mood_tags:
                is_money_gif = any(tag in existing.mood_tags.lower() for tag in ["empty", "deposit", "money"])
            else:
                is_money_gif = False
            
            if existing and is_money_gif:
                # Update existing money GIF
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
            elif existing and not is_money_gif:
                # File exists but is not a money GIF - skip to avoid overwriting regular GIF
                print(f"  ⚠️  Skipping: {filename} already exists as regular GIF (not money GIF)")
                print(f"     To convert to money GIF, delete the existing record first.")
            else:
                # Create new money GIF entry
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
        print(f"  Total files processed: {len(gif_files)}")
        
        if loaded_count > 0 or updated_count > 0:
            print("\n✅ Money GIFs loaded successfully!")
            print("\nMoney GIFs are tagged with 'empty,deposit,money' and will be")
            print("used when the bottle reaches empty (0% fullness) state.")
        
        return 0
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error loading money GIFs: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(load_money_gifs())
