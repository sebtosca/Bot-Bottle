"""Clean sticker database: remove WebP entries and ensure PNG entries have descriptions."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.db import init_db, get_session, Sticker

print("=" * 60)
print("Cleaning Sticker Database")
print("=" * 60)

# Initialize database
try:
    init_db()
    print("✅ Database initialized\n")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    sys.exit(1)

# Load descriptions
stickers_dir = Path(__file__).parent.parent / "stickers"
descriptions_file = stickers_dir / "descriptions.json"

descriptions = {}
if descriptions_file.exists():
    try:
        with open(descriptions_file, "r", encoding="utf-8") as f:
            descriptions = json.load(f)
        print(f"✅ Loaded {len(descriptions)} descriptions from descriptions.json\n")
    except Exception as e:
        print(f"⚠️  Could not load descriptions.json: {e}\n")

session = get_session()

try:
    # Get all stickers
    all_stickers = session.query(Sticker).all()
    print(f"Found {len(all_stickers)} sticker(s) in database\n")
    
    # Separate WebP and PNG
    webp_stickers = [s for s in all_stickers if s.filename.lower().endswith('.webp')]
    png_stickers = [s for s in all_stickers if s.filename.lower().endswith('.png')]
    other_stickers = [s for s in all_stickers if not s.filename.lower().endswith(('.webp', '.png'))]
    
    print(f"  WebP stickers: {len(webp_stickers)}")
    print(f"  PNG stickers: {len(png_stickers)}")
    if other_stickers:
        print(f"  Other formats: {len(other_stickers)}")
    print()
    
    # Delete WebP stickers
    deleted_count = 0
    if webp_stickers:
        print("Deleting WebP stickers...")
        for sticker in webp_stickers:
            print(f"  🗑️  Deleting: {sticker.filename}")
            session.delete(sticker)
            deleted_count += 1
        print()
    
    # Update PNG stickers with descriptions
    updated_count = 0
    if png_stickers:
        print("Updating PNG stickers with descriptions...")
        for sticker in png_stickers:
            # Get description from JSON file
            description = descriptions.get(sticker.filename)
            
            if description:
                if sticker.description != description:
                    print(f"  ✏️  Updating: {sticker.filename}")
                    print(f"     Old: {sticker.description[:50] if sticker.description else 'None'}...")
                    print(f"     New: {description[:50]}...")
                    sticker.description = description
                    updated_count += 1
                else:
                    print(f"  ✅ Already correct: {sticker.filename}")
            else:
                print(f"  ⚠️  No description found for: {sticker.filename}")
        print()
    
    # Commit changes
    session.commit()
    
    # Verify final state
    final_stickers = session.query(Sticker).all()
    final_png = [s for s in final_stickers if s.filename.lower().endswith('.png')]
    final_webp = [s for s in final_stickers if s.filename.lower().endswith('.webp')]
    
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Deleted WebP stickers: {deleted_count}")
    print(f"  Updated PNG descriptions: {updated_count}")
    print(f"  Final PNG stickers in DB: {len(final_png)}")
    print(f"  Final WebP stickers in DB: {len(final_webp)}")
    print()
    
    if final_png:
        print("✅ PNG Stickers in database:")
        for sticker in final_png:
            print(f"  - {sticker.filename}")
            print(f"    Mood: {sticker.mood_tags or 'None'}")
            print(f"    Description: {sticker.description[:60] if sticker.description else 'None'}...")
            print()
    
    if final_webp:
        print(f"⚠️  Warning: {len(final_webp)} WebP sticker(s) still in database")
    else:
        print("✅ All WebP stickers removed!")
    
    print("\n✅ Database cleaned successfully!")
    
except Exception as e:
    session.rollback()
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    session.close()




