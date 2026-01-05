#!/usr/bin/env bash

# Multi-character webhook test script for BotBottle
# Tests character switching between Cherry (00001) and Pompon (00002)
# Usage:
#   bash test_multi_character_webhook.sh
#   WEBHOOK_URL=https://investment-jamie-merge-downtown.trycloudflare.com/whatsapp-webhook bash test_multi_character_webhook.sh

WEBHOOK_URL="${WEBHOOK_URL:-https://investment-jamie-merge-downtown.trycloudflare.com/whatsapp-webhook}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"

echo "============================================================"
echo "Multi-Character Webhook Test Script"
echo "============================================================"
echo "Using webhook URL: $WEBHOOK_URL"
echo "Simulated from number: $FROM_NUMBER"
echo "============================================================"
echo

send_request_with_product_id() {
  local body="$1"
  local product_id="$2"
  local type="${3:-manual}"

  echo "============================================================"
  echo "Sending message: \"$body\""
  echo "Product ID: $product_id"
  echo "============================================================"

  # Build context JSON if product_id is provided
  local context_json=""
  if [ -n "$product_id" ]; then
    context_json=",
      \"context\": {
        \"product\": \"$product_id\"
      }"
  fi

  curl -i -X POST "$WEBHOOK_URL" \
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
                    \"id\": \"wamid.test.$type.$RANDOM\",
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
    }"

  echo
  echo "Message sent! Check your Flask server logs."
  echo
  sleep 2  # Wait 2 seconds between messages
}

echo "Step 1: Testing with Cherry (product_id=00001)"
echo "Sending: 'Bonjour'"
send_request_with_product_id "Bonjour" "00001" "cherry_test"

echo
echo "Step 2: Testing with Pompon (product_id=00002)"
echo "Sending: 'Salut'"
send_request_with_product_id "Salut" "00002" "pompon_test"

echo
echo "Step 3: Testing default (no product_id - should use Cherry)"
echo "Sending: 'Comment ça va?'"
send_request_with_product_id "Comment ça va?" "" "default_test"

echo
echo "Step 4: Testing character switch request"
echo "Sending: 'changer de personnage'"
send_request_with_product_id "changer de personnage" "00001" "switch_test"

echo
echo "============================================================"
echo "Test sequence complete!"
echo "============================================================"
echo "Check your Flask server logs to see:"
echo "  - Product ID extraction from context"
echo "  - Character selection (Cherry vs Pompon)"
echo "  - Character switching functionality"
echo "============================================================"
