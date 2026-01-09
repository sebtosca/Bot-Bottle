-- Migration script to add missing columns to users table
-- Run this script in your PostgreSQL database

-- Add total_points column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'total_points'
    ) THEN
        ALTER TABLE users ADD COLUMN total_points INTEGER NOT NULL DEFAULT 0;
        RAISE NOTICE 'Added column total_points';
    ELSE
        RAISE NOTICE 'Column total_points already exists';
    END IF;
END $$;

-- Add current_title column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'current_title'
    ) THEN
        ALTER TABLE users ADD COLUMN current_title VARCHAR;
        RAISE NOTICE 'Added column current_title';
    ELSE
        RAISE NOTICE 'Column current_title already exists';
    END IF;
END $$;

-- Add total_money_saved column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'total_money_saved'
    ) THEN
        ALTER TABLE users ADD COLUMN total_money_saved FLOAT NOT NULL DEFAULT 0.0;
        RAISE NOTICE 'Added column total_money_saved';
    ELSE
        RAISE NOTICE 'Column total_money_saved already exists';
    END IF;
END $$;

-- Add total_co2_saved column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'total_co2_saved'
    ) THEN
        ALTER TABLE users ADD COLUMN total_co2_saved FLOAT NOT NULL DEFAULT 0.0;
        RAISE NOTICE 'Added column total_co2_saved';
    ELSE
        RAISE NOTICE 'Column total_co2_saved already exists';
    END IF;
END $$;

-- Add last_notification_sent column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'last_notification_sent'
    ) THEN
        ALTER TABLE users ADD COLUMN last_notification_sent TIMESTAMP;
        RAISE NOTICE 'Added column last_notification_sent';
    ELSE
        RAISE NOTICE 'Column last_notification_sent already exists';
    END IF;
END $$;

-- Verify all columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;

