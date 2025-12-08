#!/bin/bash
# Script to set up BotBottle database

echo "Setting up BotBottle database..."

# Create user and database
sudo -u postgres psql << EOF
-- Create user (will prompt for password)
CREATE USER botbottle_user WITH PASSWORD 'botbottle_password_123';

-- Create database
CREATE DATABASE botbottle_db OWNER botbottle_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE botbottle_db TO botbottle_user;

\q
EOF

echo ""
echo "✅ Database created!"
echo ""
echo "Update your .env file with:"
echo "DATABASE_URL=postgresql+psycopg2://botbottle_user:botbottle_password_123@localhost:5432/botbottle_db"
echo ""
echo "⚠️  Remember to change the password to something secure!"

