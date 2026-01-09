# Database Migration Instructions

## Quick Fix: Run SQL Migration

The `users` table is missing required columns. Run this SQL in your PostgreSQL database:

### Option 1: Using psql command line

```bash
# Connect to your database
psql -U botbottle_user -d botbottle_db

# Then paste and run these commands:
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_points INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS current_title VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_money_saved FLOAT NOT NULL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_co2_saved FLOAT NOT NULL DEFAULT 0.0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_notification_sent TIMESTAMP;
```

### Option 2: Run the SQL file

```bash
psql -U botbottle_user -d botbottle_db -f migrate_users_table.sql
```

### Option 3: Run Python script from WSL

If you're in WSL where your Flask server runs:

```bash
cd /mnt/c/Users/SebastienToscano/BotBottle
python3 migrate_add_user_columns.py
```

Or if you're using a conda/virtual environment:

```bash
cd /mnt/c/Users/SebastienToscano/BotBottle
source ~/anaconda3/bin/activate  # or your venv activation
python migrate_add_user_columns.py
```

## Verify Migration

After running the migration, verify the columns exist:

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
```

You should see all 5 new columns listed.

