#!/usr/bin/env bash

# Test script to send a webhook message with Pompon (product_id=00002)
# This will trigger the bot to send Pompon stickers

WEBHOOK_URL="${WEBHOOK_URL:-https://investment-jamie-merge-downtown.trycloudflare.com/whatsapp-webhook}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"

echo "============================================================"
echo "Testing Pompon Sticker Sending"
echo "============================================================"
echo "Using webhook URL: $WEBHOOK_URL"
echo "Product ID: 00002 (Pompon)"
echo "============================================================"
echo

echo "Sending test message with Pompon context..."
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
                  \"id\": \"wamid.test.pompon.$(date +%s)\",
                  \"timestamp\": \"$(date +%s)\",
                  \"type\": \"text\",
                  \"text\": { 
                    \"body\": \"Salut Pompon ! Comment vas-tu ?\"
                  },
                  \"context\": {
                    \"product\": \"00002\"
                  }
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
echo
echo "============================================================"
echo "Message sent!"
echo "============================================================"
echo "Check your Flask server logs to see:"
echo "  - Product ID extraction: 00002"
echo "  - Character ID: 00002 (Pompon)"
echo "  - Sticker selection for Pompon"
echo "  - Sticker URLs should point to Pompon stickers"
echo
echo "If your Flask server is running and connected to WhatsApp,"
echo "you should receive a message with Pompon stickers!"
echo "============================================================"
