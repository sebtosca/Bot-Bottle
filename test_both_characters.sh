#!/usr/bin/env bash

# Test script to verify both Cherry and Pompon work together
# This script tests:
# 1. Creating both characters for the same user
# 2. Sending messages to each character
# 3. Character switching
# 4. Verifying each character uses their own assets

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
echo "Testing Both Characters (Cherry & Pompon)"
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
echo "  1. Create Cherry (product_id=00001) with first message"
echo "  2. Create Pompon (product_id=00002) with first message"
echo "  3. Send message to Cherry (verify Cherry responds)"
echo "  4. Send message to Pompon (verify Pompon responds)"
echo "  5. Test character switching"
echo "  6. Test insult to Cherry (should get angry_cherry.webp)"
echo "  7. Test insult to Pompon (should get angry_cider.webp)"
echo "  8. Test happy message to both"
echo
read -p "Press Enter to start the test..."
echo

# Step 1: Create Cherry
send_message "Bonjour, je suis Cherry" "00001" "1"

# Step 2: Create Pompon
send_message "Boujou, je suis Pompon" "00002" "2"

# Step 3: Message to Cherry
send_message "Salut Cherry, comment ça va?" "00001" "3"

# Step 4: Message to Pompon
send_message "Salut Pompon, ça va?" "00002" "4"

# Step 5: Test character switching (from Cherry context)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Testing Character Switch"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
send_message "changer de personnage" "00001" "5a"
sleep 5  # Wait longer for interactive response

# Step 6: Test insult to Cherry (should trigger angry_cherry.webp)
send_message "tu es un connard" "00001" "6"

# Step 7: Test insult to Pompon (should trigger angry_cider.webp)
send_message "tu es un connard" "00002" "7"

# Step 8: Test happy message to Cherry
send_message "je t'aime beaucoup!" "00001" "8a"

# Step 9: Test happy message to Pompon
send_message "je t'aime beaucoup!" "00002" "8b"

echo "============================================================"
echo "✅ Test sequence complete!"
echo "============================================================"
echo
echo "📊 Expected Results:"
echo "  ✓ Both characters created in database"
echo "  ✓ Cherry uses: happy_cherry.webp, angry_cherry.webp, Cherry GIFs"
echo "  ✓ Pompon uses: happy_cider.webp, angry_cider.webp, Pompon GIFs"
echo "  ✓ Character switching works"
echo "  ✓ Each character responds with correct assets"
echo
echo "Check your Flask server logs to verify:"
echo "  - Character IDs in responses"
echo "  - Sticker filenames (cherry vs cider)"
echo "  - GIF directories (Cherry_GIF/ vs pompon_GIF/)"
echo "  - Character-specific system prompts"
echo "============================================================"
