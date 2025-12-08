#!/usr/bin/env bash

# Simple webhook test script for BotBottle
# Usage:
#   bash test_webhook.sh               # uses default URL, prompts for message
#   WEBHOOK_URL=http://localhost:5000/whatsapp-webhook bash test_webhook.sh
#   WEBHOOK_URL=https://your-tunnel-url.trycloudflare.com/whatsapp-webhook bash test_webhook.sh

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5000/whatsapp-webhook}"
FROM_NUMBER="${FROM_NUMBER:-33684950535}"

echo "============================================================"
echo "WhatsApp Webhook Test Script"
echo "============================================================"
echo "Using webhook URL: $WEBHOOK_URL"
echo "Simulated from number: $FROM_NUMBER"
echo "============================================================"
echo

send_request() {
  local body="$1"
  local type="${2:-manual}"

  echo "============================================================"
  echo "Sending message: \"$body\""
  echo "============================================================"

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
                    \"text\": { \"body\": \"$body\" }
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
  echo "Message sent! Check your Flask server logs and your WhatsApp for replies."
  echo
}

# Interactive mode: prompt for message
if [ $# -eq 0 ]; then
  while true; do
    echo "Enter a message to send (or 'quit'/'exit' to stop):"
    read -r message_body
    
    if [ -z "$message_body" ]; then
      echo "Message cannot be empty. Please try again."
      continue
    fi
    
    if [ "$message_body" = "quit" ] || [ "$message_body" = "exit" ]; then
      echo "Exiting..."
      break
    fi
    
    send_request "$message_body"
  done
else
  # Command-line mode: use first argument as message
  send_request "$1"
fi