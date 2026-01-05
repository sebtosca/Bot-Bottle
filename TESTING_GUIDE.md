# Testing Guide: Multi-Character Points & Rewards System

This guide explains how to test the new points and rewards system with both Cherry and Pompon.

## Prerequisites

1. **Database Migration**: Run the migration script first:
   ```bash
   python scripts/migrate_add_points_system.py
   ```

2. **Flask Server Running**: Make sure your Flask server is running:
   ```bash
   python -m endpoint.endpoint
   ```

3. **Cloudflare Tunnel** (if testing via WhatsApp): Make sure your tunnel is active:
   ```bash
   cloudflared tunnel --url http://localhost:5000
   ```

## Testing Methods

### Method 1: Automated Test Script

Run the comprehensive test script:

```bash
bash test_points_system.sh
```

This script tests:
- Character collection (100 points each)
- Milestone bonuses (50/100/200 points)
- Feeding points (10 points per feed)
- Stats command
- Promo codes
- Character selection for feeding

### Method 2: Interactive Testing

Use the interactive webhook test script:

```bash
bash test_webhook.sh
```

**Commands:**
- Type `cherry` or `1` to switch to Cherry
- Type `pompon` or `2` to switch to Pompon
- Type `switch` to toggle between characters
- Type any message to send it
- Type `quit` to exit

**Example Flow:**
```
[Cherry] Enter a message: Bonjour
[Cherry] Enter a message: pompon
[Pompon] Enter a message: Salut
[Pompon] Enter a message: mes statistiques
[Pompon] Enter a message: 🍎🍎🍎
```

### Method 3: Manual WhatsApp Testing

If you have WhatsApp Cloud API configured:

1. **Create Cherry**: Send a message with Cherry's product link
   - Should award 100 points for character collection
   - Should start the game

2. **Create Pompon**: Send a message with Pompon's product link
   - Should award 100 points + 50 milestone bonus (2 characters)
   - Should start the game

3. **Check Stats**: Send "mes statistiques" or "mes points"
   - Should show: points, title, money saved, CO2 saved, character count

4. **Feed Characters**: Send emojis (🍎🍎🍎)
   - If you have both characters: Should show selection buttons
   - Should award 10 points per successful feed (3 correct emojis)

5. **Check Promos**: Send "mes promos"
   - Should show available promo codes based on your title level

6. **Test Character Switch**: Send "changer de personnage"
   - Should show buttons to select character

## Testing Points System

### Points Values

- **Character Collection**: 100 points per character
- **Feeding**: 10 points per successful feed (3 correct emojis)
- **Daily Engagement**: 5 points per day
- **Bottle Return**: 500 points (verified receipt)
- **Milestone Bonuses**:
  - 2 characters: +50 points
  - 3 characters: +100 points
  - 4+ characters: +200 points

### Title Levels

- **Novice**: 0-499 points
- **Apprentice**: 500-1999 points
- **Master**: 2000+ points

### Testing Checklist

- [ ] Character collection awards 100 points
- [ ] Milestone bonuses are awarded correctly
- [ ] Feeding awards 10 points per feed
- [ ] Stats command shows correct information
- [ ] Title updates automatically based on points
- [ ] Promo codes are shown based on title level
- [ ] Character selection works when multiple characters exist
- [ ] Unified notifications work for multiple hungry characters
- [ ] Daily engagement points are awarded (test next day)

## Testing Receipt Verification

To test receipt verification:

1. **Start a character** (Cherry or Pompon)
2. **Send an image** of a receipt
3. **Expected behavior**:
   - Image is downloaded from WhatsApp
   - OCR extracts text using Mistral Vision
   - Receipt is verified
   - 500 points are awarded
   - Money and CO2 savings are calculated
   - Bottle is marked as returned

**Note**: Receipt verification requires:
- `MISTRAL_API_KEY` set in `.env`
- Valid receipt image with keywords like "bouteille", "consigne", "retour"

## Verifying Database State

Check the database to verify points and stats:

```bash
python test_both_characters_db.py
```

Or manually query:

```python
from db.db import init_db, get_session
from points_system import get_user_stats

init_db()
session = get_session()

# Get user stats
stats = get_user_stats(session, user_id=1)
print(stats)
```

## Common Issues

### Points Not Awarded

- Check Flask server logs for errors
- Verify database migration completed successfully
- Check that `game_started=True` for the character

### Stats Not Showing

- Verify the stats command keywords: "mes statistiques", "mes points", "statistiques"
- Check that user has at least one character

### Character Selection Not Working

- Ensure you have 2+ characters with `game_started=True`
- Check that you're sending emojis (not just text)
- Verify interactive buttons are enabled in WhatsApp Cloud API

### Receipt Verification Failing

- Check `MISTRAL_API_KEY` is set
- Verify image is accessible (WhatsApp media URLs expire after 5 minutes)
- Check OCR text extraction in logs

## Next Steps

After testing:

1. **Monitor Points**: Check that points accumulate correctly
2. **Test Title Progression**: Reach 500 points to become Apprentice
3. **Test Milestones**: Collect 3+ characters to test milestone bonuses
4. **Test Receipt Verification**: Send actual receipt images
5. **Test Promo Codes**: Verify codes are shown based on title level
