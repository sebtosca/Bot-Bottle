#!/usr/bin/env bash

# Test webhook script to send an emoji
# Usage:
#   bash test_webhook_emoji.sh               # uses default URL
#   WEBHOOK_URL=http://localhost:5000/whatsapp-webhook bash test_webhook_emoji.sh
#   WEBHOOK_URL=https://your-tunnel-url.trycloudflare.com/whatsapp-webhook bash test_webhook_emoji.sh

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5000/whatsapp-webhook}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"

# The grinning face emoji 😁
EMOJI="😁"

echo "============================================================"
echo "WhatsApp Webhook Emoji Test"
echo "============================================================"
echo "Using webhook URL: $WEBHOOK_URL"
echo "Simulated from number: $FROM_NUMBER"
echo "Sending emoji: $EMOJI"
echo "============================================================"
echo

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
                  \"id\": \"wamid.test.emoji.$RANDOM\",
                  \"timestamp\": \"$(date +%s)\",
                  \"type\": \"text\",
                  \"text\": { \"body\": \"$EMOJI\" }
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
echo "Emoji sent! Check your Flask server logs and your WhatsApp for replies."
echo
