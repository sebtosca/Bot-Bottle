#!/usr/bin/env python3
"""Load enhanced GIF descriptions into the database.

This script:
1. Deletes old GIF entries from the database
2. Loads new enhanced GIF descriptions from Cherry and Pompon JSON files
3. Maps enhanced structure to database fields (description, mood_tags, character_id)
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import DATABASE_URL
from db.db import init_db, get_session, Sticker
from models.characters import CHARACTERS

# Character ID mappings
CHARACTER_IDS = {
    "Cherry": "00001",
    "Pompon": "00002"
}

# GIF directory mappings
GIF_DIRECTORIES = {
    "00001": project_root / "Cherry_GIF",
    "00002": project_root / "pompon_GIF"
}

# Enhanced JSON file mappings
ENHANCED_JSON_FILES = {
    "00001": project_root / "Cherry_GIF" / "GIF_descriptions_enhanced.json",
    "00002": project_root / "pompon_GIF" / "pompon_gif_description_enhanced.json"
}


def delete_old_gifs(session, character_id=None):
    """Delete old GIF entries from database.
    
    Args:
        session: Database session
        character_id: Optional character ID to filter by. If None, deletes all GIFs.
    
    Returns:
        Number of GIFs deleted
    """
    query = session.query(Sticker).filter(Sticker.media_type == "gif")
    
    if character_id:
        query = query.filter(Sticker.character_id == character_id)
    
    count = query.count()
    
    if count > 0:
        query.delete()
        session.commit()
        print(f"  🗑️  Deleted {count} old GIF(s) for character {character_id or 'all'}")
    else:
        print(f"  ℹ️  No old GIFs found for character {character_id or 'all'}")
    
    return count


def load_enhanced_gifs_for_character(session, character_id, character_name):
    """Load enhanced GIF descriptions for a specific character.
    
    Args:
        session: Database session
        character_id: Character ID (e.g., "00001" for Cherry)
        character_name: Character name for display
    
    Returns:
        Number of GIFs loaded
    """
    json_file = ENHANCED_JSON_FILES.get(character_id)
    gif_dir = GIF_DIRECTORIES.get(character_id)
    
    if not json_file or not json_file.exists():
        print(f"  ❌ Enhanced JSON file not found: {json_file}")
        return 0
    
    if not gif_dir or not gif_dir.exists():
        print(f"  ❌ GIF directory not found: {gif_dir}")
        return 0
    
    print(f"\n  📂 Loading GIFs from: {json_file.name}")
    print(f"  📁 GIF directory: {gif_dir.name}")
    
    # Load enhanced JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            enhanced_data = json.load(f)
    except Exception as e:
        print(f"  ❌ Error loading JSON: {e}")
        return 0
    
    loaded_count = 0
    skipped_count = 0
    error_count = 0
    
    # Process each GIF
    for filename, gif_data in enhanced_data.items():
        try:
            # Check if file exists in directory
            gif_path = gif_dir / filename
            if not gif_path.exists():
                print(f"    ⚠️  File not found, skipping: {filename}")
                skipped_count += 1
                continue
            
            # Extract data from enhanced structure
            description = gif_data.get("description", "")
            mood_tags = gif_data.get("mood_tags", "")
            
            # Check if GIF already exists
            existing = session.query(Sticker).filter(
                Sticker.filename == filename,
                Sticker.character_id == character_id,
                Sticker.media_type == "gif"
            ).first()
            
            if existing:
                # Update existing entry
                existing.description = description
                existing.mood_tags = mood_tags
                print(f"    ✏️  Updated: {filename[:50]}...")
            else:
                # Create new entry
                new_gif = Sticker(
                    filename=filename,
                    character_id=character_id,
                    media_type="gif",
                    description=description,
                    mood_tags=mood_tags,
                    url=None  # Legacy field, not used
                )
                session.add(new_gif)
                print(f"    ✅ Added: {filename[:50]}...")
            
            loaded_count += 1
            
        except Exception as e:
            print(f"    ❌ Error processing {filename}: {e}")
            error_count += 1
            continue
    
    # Commit all changes
    try:
        session.commit()
        print(f"\n  ✅ Successfully loaded {loaded_count} GIF(s)")
        if skipped_count > 0:
            print(f"  ⚠️  Skipped {skipped_count} GIF(s) (file not found)")
        if error_count > 0:
            print(f"  ❌ Errors: {error_count} GIF(s)")
    except Exception as e:
        session.rollback()
        print(f"  ❌ Error committing to database: {e}")
        return 0
    
    return loaded_count


def main():
    """Main function to load enhanced GIF descriptions."""
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set")
        return 1
    
    print("=" * 60)
    print("Loading Enhanced GIF Descriptions")
    print("=" * 60)
    
    try:
        init_db()
        session = get_session()
        
        # Count existing GIFs
        total_gifs_before = session.query(Sticker).filter(Sticker.media_type == "gif").count()
        cherry_gifs_before = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.character_id == "00001"
        ).count()
        pompon_gifs_before = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.character_id == "00002"
        ).count()
        
        print(f"\n📊 Current GIFs in database:")
        print(f"  Total: {total_gifs_before}")
        print(f"  - Cherry (00001): {cherry_gifs_before}")
        print(f"  - Pompon (00002): {pompon_gifs_before}")
        
        # Delete old GIFs
        print(f"\n🗑️  Deleting old GIFs...")
        delete_old_gifs(session, character_id="00001")
        delete_old_gifs(session, character_id="00002")
        
        # Load enhanced GIFs for each character
        total_loaded = 0
        
        print(f"\n📥 Loading enhanced GIF descriptions...")
        
        # Load Cherry GIFs
        print(f"\n🍒 Loading Cherry GIFs...")
        cherry_loaded = load_enhanced_gifs_for_character(session, "00001", "Cherry")
        total_loaded += cherry_loaded
        
        # Load Pompon GIFs
        print(f"\n🍎 Loading Pompon GIFs...")
        pompon_loaded = load_enhanced_gifs_for_character(session, "00002", "Pompon")
        total_loaded += pompon_loaded
        
        # Final summary
        total_gifs_after = session.query(Sticker).filter(Sticker.media_type == "gif").count()
        cherry_gifs_after = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.character_id == "00001"
        ).count()
        pompon_gifs_after = session.query(Sticker).filter(
            Sticker.media_type == "gif",
            Sticker.character_id == "00002"
        ).count()
        
        print("\n" + "=" * 60)
        print("Loading Summary")
        print("=" * 60)
        print(f"  Total loaded: {total_loaded}")
        print(f"  - Cherry: {cherry_loaded}")
        print(f"  - Pompon: {pompon_loaded}")
        print(f"\n📊 GIFs in database after loading:")
        print(f"  Total: {total_gifs_after}")
        print(f"  - Cherry (00001): {cherry_gifs_after}")
        print(f"  - Pompon (00002): {pompon_gifs_after}")
        
        session.close()
        
        print("\n✅ Enhanced GIF descriptions loaded successfully!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
