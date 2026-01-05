#!/usr/bin/env bash

# Comprehensive test script for Points & Rewards System with both characters
# Tests:
# 1. Character collection (points)
# 2. Feeding (points)
# 3. Stats command
# 4. Unified notifications
# 5. Character selection for feeding
# 6. Promo codes
# 7. Daily engagement

# Load PUBLIC_BASE_URL from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
  PUBLIC_BASE_URL=$(grep "^PUBLIC_BASE_URL=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- | sed "s/^['\"]//;s/['\"]$//" | tr -d '[:space:]')
fi

if [ -n "$PUBLIC_BASE_URL" ]; then
  DEFAULT_WEBHOOK_URL="${PUBLIC_BASE_URL%/}/whatsapp-webhook"
else
  DEFAULT_WEBHOOK_URL="http://localhost:5000/whatsapp-webhook"
fi

WEBHOOK_URL="${WEBHOOK_URL:-$DEFAULT_WEBHOOK_URL}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"

echo "============================================================"
echo "Testing Points & Rewards System with Both Characters"
echo "============================================================"
echo "Webhook URL: $WEBHOOK_URL"
echo "From number: $FROM_NUMBER"
echo "============================================================"
echo

send_message() {
  local body="$1"
  local product_id="$2"
  local step="$3"
  
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "STEP $step: $body"
  echo "Product ID: ${product_id:-'default (Cherry)'}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  
  local context_json=""
  if [ -n "$product_id" ]; then
    context_json=",
      \"context\": {
        \"product\": \"$product_id\"
      }"
  fi

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
                    \"id\": \"wamid.test.$step.$RANDOM\",
                    \"timestamp\": \"$(date +%s)\",
                    \"type\": \"text\",
                    \"text\": { \"body\": \"$body\" }$context_json
                  }
                ]
              },
              \"field\": \"messages\"
            }
          ]
        }
      ]
    }" > /dev/null

  echo "✅ Message sent"
  echo
  sleep 3  # Wait 3 seconds between messages
}

echo "📋 Test Plan:"
echo "  Phase 1: Character Collection & Points"
echo "    1. Create Cherry (should award 100 points for collection)"
echo "    2. Create Pompon (should award 100 points + milestone bonus)"
echo "    3. Check stats (should show points and title)"
echo ""
echo "  Phase 2: Feeding & Points"
echo "    4. Feed Cherry with correct emojis (should award 10 points per feed)"
echo "    5. Feed Pompon with correct emojis (should award 10 points per feed)"
echo "    6. Test character selection when sending emojis with both characters"
echo ""
echo "  Phase 3: Stats & Promos"
echo "    7. Check stats command (mes statistiques)"
echo "    8. Check promo codes (mes promos)"
echo ""
echo "  Phase 4: Emotional Responses & Stickers/GIFs"
echo "    9. Test angry message (should trigger angry sticker)"
echo "    10. Test happy message (should trigger happy sticker)"
echo "    11. Test sad message (should trigger sad sticker)"
echo ""
echo "  Phase 5: Additional Features"
echo "    12. Test character switch"
echo "    13. Test rules request"
echo ""
echo "============================================================"
echo

read -p "Press Enter to start testing..."
echo

# Phase 1: Character Collection
echo "🎯 PHASE 1: Character Collection & Points"
echo "============================================================"

echo "Step 1: Creating Cherry (product_id=00001)"
echo "  Expected: 100 points for character collection"
send_message "Bonjour" "00001" "cherry_collect"

echo "Step 2: Creating Pompon (product_id=00002)"
echo "  Expected: 100 points + 50 milestone bonus (2 characters)"
send_message "Salut" "00002" "pompon_collect"

echo "Step 3: Checking stats"
echo "  Expected: Show total points, title, character count"
send_message "mes statistiques" "" "check_stats_1"

sleep 5

# Phase 2: Feeding & Points
echo ""
echo "🍽️  PHASE 2: Feeding & Points"
echo "============================================================"

echo "Step 4: Feeding Cherry with correct emojis"
echo "  Expected: 10 points per successful feed (3 correct emojis)"
echo "  Sending: 🍎🍎🍎 (assuming GREEN is correct)"
send_message "🍎🍎🍎" "00001" "feed_cherry"

sleep 3

echo "Step 5: Feeding Pompon with correct emojis"
echo "  Expected: 10 points per successful feed"
send_message "🍎🍎🍎" "00002" "feed_pompon"

sleep 3

echo "Step 6: Testing character selection (send emojis without product_id)"
echo "  Expected: Show buttons to select which character to feed"
echo "  Note: This only works if both characters are active"
send_message "🍎🍎🍎" "" "feed_selection"

sleep 5

# Phase 3: Stats & Promos
echo ""
echo "📊 PHASE 3: Stats & Promos"
echo "============================================================"

echo "Step 7: Checking stats again"
echo "  Expected: Updated points, title progression"
send_message "mes points" "" "check_stats_2"

sleep 3

echo "Step 8: Checking promo codes"
echo "  Expected: Show available promo codes based on title"
send_message "mes promos" "" "check_promos"

sleep 3

# Phase 4: Emotional Responses & Stickers/GIFs
echo ""
echo "😊 PHASE 4: Emotional Responses & Stickers/GIFs"
echo "============================================================"

echo "Step 9: Testing angry message to Cherry"
echo "  Expected: Angry sticker + appropriate response"
send_message "tu es un connard" "00001" "angry_cherry"

sleep 3

echo "Step 10: Testing happy message to Pompon"
echo "  Expected: Happy sticker + appropriate response"
send_message "je suis vraiment content de te voir" "00002" "happy_pompon"

sleep 3

echo "Step 11: Testing sad message"
echo "  Expected: Sad sticker + appropriate response"
send_message "je suis vraiment désolé" "" "sad_message"

sleep 3

# Phase 5: Additional Features
echo ""
echo "🔄 PHASE 5: Additional Features"
echo "============================================================"

echo "Step 12: Testing character switch"
echo "  Expected: Switch between characters"
send_message "changer de personnage" "" "switch_char"

sleep 3

echo "Step 13: Testing rules request"
echo "  Expected: Send rules image"
send_message "règles" "" "rules_request"

sleep 3

echo ""
echo "============================================================"
echo "✅ Testing Complete!"
echo "============================================================"
echo ""
echo "Check your Flask server logs and database to verify:"
echo "  - Points were awarded correctly"
echo "  - Titles were updated"
echo "  - Stats are displayed correctly"
echo "  - Promo codes are shown based on level"
echo ""
echo "To verify database state, run:"
echo "  python test_both_characters_db.py"
echo ""
