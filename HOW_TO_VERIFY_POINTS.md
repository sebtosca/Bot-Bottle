# How to Verify Points System is Working

## Quick Verification Methods

### 1. **Check Database Directly** (Fastest)
```bash
python verify_points_system.py
```

Or for a specific user:
```bash
python verify_points_system.py 33684950535
```

This will show:
- Current total points
- Current title (Novice/Apprentice/Master)
- Points per character
- Money and CO2 saved
- Title progress

### 2. **Ask the Bot** (User-facing)
Send one of these messages to the bot:
- `mes statistiques`
- `mes points`
- `mes stats`
- `statistiques`

The bot will respond with your current stats including points, title, and savings.

### 3. **Check Flask Server Logs**
When points are awarded, you'll see messages like:
```
🎯 Points awarded for character collection: 100
🎯 Points awarded for feeding: 10
🎯 Milestone bonus awarded: 50
```

### 4. **Test Points Awarding**

#### Test Character Collection (100 points)
1. Start a new character (Cherry or Pompon)
2. Points should be awarded when the game starts
3. Check with: `python verify_points_system.py`

#### Test Feeding (10 points per successful feed)
1. Send 3 correct emojis to feed a character
2. Points are awarded when fullness increases
3. Check stats: send `mes points` to the bot

#### Test Daily Engagement (5 points per day)
1. Interact with the bot on a new day
2. Points are automatically awarded
3. Check with verification script

#### Test Milestone Bonus
- 2 characters: +50 points
- 3 characters: +100 points
- 4+ characters: +200 points

## Points Values Reference

| Activity | Points |
|----------|--------|
| Character Collected | 100 |
| Successful Feed (3 correct emojis) | 10 |
| Daily Engagement | 5 |
| Bottle Return (verified) | 500 |
| Milestone: 2 characters | +50 |
| Milestone: 3 characters | +100 |
| Milestone: 4+ characters | +200 |

## Title Thresholds

| Title | Points Required |
|-------|----------------|
| Novice | 0+ |
| Apprentice | 500+ |
| Master | 2000+ |

## Troubleshooting

### Points not increasing?
1. Check Flask server logs for errors
2. Verify database connection: `python verify_points_system.py`
3. Check if `award_points()` is being called in logs
4. Verify user exists in database

### Stats command not working?
1. Make sure you're using French keywords: `mes statistiques`
2. Check Flask server logs for errors
3. Verify `get_user_stats()` is being called

### Points seem incorrect?
1. Run verification script to see breakdown
2. Check if milestone bonuses were awarded
3. Verify character count matches expected points

## Example Test Flow

```bash
# 1. Check initial state
python verify_points_system.py

# 2. Send test messages via webhook
bash test_points_system.sh

# 3. Check updated points
python verify_points_system.py

# 4. Or ask the bot directly
# Send: "mes statistiques"
```

