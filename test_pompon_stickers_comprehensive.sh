#!/usr/bin/env bash

# Comprehensive test script for Pompon stickers
# Tests both emotional stickers and feeding game stickers

# Load PUBLIC_BASE_URL from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  # Extract PUBLIC_BASE_URL from .env file
  PUBLIC_BASE_URL=$(grep "^PUBLIC_BASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed "s/^['\"]//;s/['\"]$//" | tr -d '[:space:]')
fi

# Construct webhook URL from PUBLIC_BASE_URL or use default
if [ -n "$PUBLIC_BASE_URL" ]; then
  DEFAULT_WEBHOOK_URL="${PUBLIC_BASE_URL%/}/whatsapp-webhook"
else
  DEFAULT_WEBHOOK_URL="http://localhost:5000/whatsapp-webhook"
fi

WEBHOOK_URL="${WEBHOOK_URL:-$DEFAULT_WEBHOOK_URL}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"
PRODUCT_ID="00002"  # Pompon

echo "============================================================"
echo "🧪 Comprehensive Pompon Sticker Test"
echo "============================================================"
echo "Webhook URL: $WEBHOOK_URL"
echo "Product ID: $PRODUCT_ID (Pompon)"
echo "From Number: $FROM_NUMBER"
echo "============================================================"
echo

# Function to send a webhook message
send_message() {
  local message="$1"
  local product_id="${2:-$PRODUCT_ID}"
  local message_id="wamid.test.pompon.$(date +%s).$$"
  
  echo "📤 Sending: \"$message\""
  echo "   Product ID: $product_id"
  
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{
      \"object\": \"whatsapp_business_account\",
      \"entry\": [
        {
          \"id\": \"test_waba\",
          \"changes\": [
            {
              \"value\": {
                \"messaging_product\": \"whatsapp\",
                \"contacts\": [
                  {
                    \"profile\": { \"name\": \"Test User\" },
                    \"wa_id\": \"$FROM_NUMBER\"
                  }
                ],
                \"messages\": [
                  {
                    \"from\": \"$FROM_NUMBER\",
                    \"id\": \"$message_id\",
                    \"timestamp\": \"$(date +%s)\",
                    \"type\": \"text\",
                    \"text\": { 
                      \"body\": \"$message\"
                    },
                    \"context\": {
                      \"product\": \"$product_id\"
                    }
                  }
                ]
              },
              \"field\": \"messages\"
            }
          ]
        }
      ]
    }" > /dev/null
  
  echo "   ✅ Message sent"
  echo
  sleep 2  # Wait 2 seconds between messages
}

echo "Step 1: Verify Pompon stickers are loaded in database"
echo "------------------------------------------------------------"
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('$SCRIPT_DIR')))
from db.db import init_db, get_session, Sticker

init_db()
session = get_session()
pompon_stickers = session.query(Sticker).filter_by(character_id='00002').all()
emotional = [s for s in pompon_stickers if s.media_type == 'sticker' and s.mood_tags and any(m in s.mood_tags.lower() for m in ['happy', 'angry', 'sad', 'scared'])]
feeding = [s for s in pompon_stickers if 'GREEN' in (s.mood_tags or '') or 'YELLOW' in (s.mood_tags or '') or 'BLUE' in (s.mood_tags or '') or 'BLACK' in (s.mood_tags or '')]

print(f'  Total Pompon stickers: {len(pompon_stickers)}')
print(f'  Emotional stickers: {len(emotional)}')
print(f'  Feeding game stickers: {len(feeding)}')
print()

if len(pompon_stickers) == 0:
    print('  ❌ No Pompon stickers found in database!')
    print('  Run these scripts to load stickers:')
    print('    python scripts/load_pompon_emotional_stickers.py')
    print('    python scripts/load_pompon_feeding_stickers.py')
    sys.exit(1)
else:
    print('  ✅ Pompon stickers are loaded')
    print()
"

if [ $? -ne 0 ]; then
  echo "❌ Database check failed. Please load Pompon stickers first."
  exit 1
fi

echo
echo "Step 2: Test Emotional Stickers"
echo "------------------------------------------------------------"
echo "Testing different moods to trigger emotional stickers..."
echo

# Test happy mood
send_message "Salut Pompon ! Je suis content de te voir ! 😊" "$PRODUCT_ID"

# Test angry mood
send_message "Tu es un connard !" "$PRODUCT_ID"

# Test sad mood
send_message "Je suis triste aujourd'hui..." "$PRODUCT_ID"

# Test neutral conversation
send_message "Comment vas-tu ?" "$PRODUCT_ID"

echo
echo "Step 3: Test Feeding Game Stickers"
echo "------------------------------------------------------------"
echo "Sending emojis to trigger feeding game stickers..."
echo

# Send emojis for different colors (these should trigger feeding stickers)
send_message "🟢" "$PRODUCT_ID"  # Green (glass)
send_message "🟡" "$PRODUCT_ID"  # Yellow (plastic)
send_message "🔵" "$PRODUCT_ID"  # Blue (paper/cardboard)
send_message "⚫" "$PRODUCT_ID"  # Black (non-recyclable)

echo
echo "Step 4: Test Mixed Messages (Text + Emoji)"
echo "------------------------------------------------------------"
echo "Sending messages that should trigger both text response and stickers..."
echo

send_message "Voici un cadeau pour toi 🟢🟡" "$PRODUCT_ID"
send_message "Je t'aime beaucoup ! 💚" "$PRODUCT_ID"

echo
echo "============================================================"
echo "✅ Test Complete!"
echo "============================================================"
echo
echo "Check your Flask server logs and WhatsApp messages to verify:"
echo "  ✓ Emotional stickers are sent (happy, angry, sad, etc.)"
echo "  ✓ Feeding game stickers are sent when emojis are received"
echo "  ✓ Stickers are from Pompon (character_id=00002)"
echo "  ✓ Sticker URLs point to Pompon directories"
echo
echo "If stickers are not appearing:"
echo "  1. Check Flask server logs for errors"
echo "  2. Verify stickers are loaded: python scripts/load_pompon_emotional_stickers.py"
echo "  3. Verify feeding stickers: python scripts/load_pompon_feeding_stickers.py"
echo "  4. Check that endpoint is running: python -m endpoint.endpoint"
echo "============================================================"

