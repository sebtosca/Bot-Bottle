# Loading Enhanced GIF Descriptions

## Overview

The `load_enhanced_gifs.py` script removes old GIF descriptions from the database and loads the new enhanced descriptions from the JSON files.

## What It Does

1. **Deletes old GIF entries** from the database (only GIFs, preserves stickers)
2. **Loads enhanced descriptions** from:
   - `Cherry_GIF/GIF_descriptions_enhanced.json`
   - `pompon_GIF/pompon_gif_description_enhanced.json`
3. **Maps enhanced structure** to database fields:
   - `description` - Full French description
   - `mood_tags` - Comma-separated mood tags
   - `character_id` - Character ID (00001 for Cherry, 00002 for Pompon)
   - `filename` - GIF filename (must exist in directory)
   - `media_type` - Set to "gif"

## Usage

```bash
python scripts/load_enhanced_gifs.py
```

## Requirements

- `DATABASE_URL` must be set in `.env` or environment
- Enhanced JSON files must exist:
  - `Cherry_GIF/GIF_descriptions_enhanced.json`
  - `pompon_GIF/pompon_gif_description_enhanced.json`
- GIF files must exist in their respective directories

## What Gets Loaded

The script extracts from the enhanced JSON structure:
- `description` → Database `description` field
- `mood_tags` → Database `mood_tags` field (comma-separated string)

**Note**: The enhanced JSON contains additional fields (intent, intensity, use_cases, etc.) that are not stored in the database. These are for future use or can be stored separately if needed.

## Safety

- Only deletes GIFs (`media_type == "gif"`), preserves all stickers
- Verifies files exist before loading
- Shows detailed progress and summary
- Rolls back on errors

## Example Output

```
============================================================
Loading Enhanced GIF Descriptions
============================================================

📊 Current GIFs in database:
  Total: 46
  - Cherry (00001): 25
  - Pompon (00002): 21

🗑️  Deleting old GIFs...
  🗑️  Deleted 25 old GIF(s) for character 00001
  🗑️  Deleted 21 old GIF(s) for character 00002

📥 Loading enhanced GIF descriptions...

🍒 Loading Cherry GIFs...
  📂 Loading GIFs from: GIF_descriptions_enhanced.json
  📁 GIF directory: Cherry_GIF
    ✅ Added: Ajff GIF by Atlanta Jewish Film Festival_whatsapp.mp4...
    ✅ Added: Animated GIF_whatsapp.mp4...
    ...

  ✅ Successfully loaded 25 GIF(s)

🍎 Loading Pompon GIFs...
  📂 Loading GIFs from: pompon_gif_description_enhanced.json
  📁 GIF directory: pompon_GIF
    ✅ Added: Angry Loki GIF_whatsapp.mp4...
    ✅ Added: angry pub GIF by Bouygues Telecom_whatsapp.mp4...
    ...

  ✅ Successfully loaded 21 GIF(s)

============================================================
Loading Summary
============================================================
  Total loaded: 46
  - Cherry: 25
  - Pompon: 21

📊 GIFs in database after loading:
  Total: 46
  - Cherry (00001): 25
  - Pompon (00002): 21

✅ Enhanced GIF descriptions loaded successfully!
```
