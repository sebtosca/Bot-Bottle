#!/usr/bin/env bash

# Simple webhook test script for BotBottle with character switching
# Usage:
#   bash test_webhook.sh               # uses PUBLIC_BASE_URL from .env, prompts for message
#   WEBHOOK_URL=http://localhost:5000/whatsapp-webhook bash test_webhook.sh
#   WEBHOOK_URL=https://your-tunnel-url.trycloudflare.com/whatsapp-webhook bash test_webhook.sh

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

# Current character (default: Cherry)
CURRENT_CHARACTER="Cherry"
CURRENT_PRODUCT_ID="00001"

echo "============================================================"
echo "WhatsApp Webhook Test Script"
echo "============================================================"
echo "Using webhook URL: $WEBHOOK_URL"
echo "Simulated from number: $FROM_NUMBER"
echo "Current character: $CURRENT_CHARACTER (product_id=$CURRENT_PRODUCT_ID)"
echo "============================================================"
echo
echo "Commands:"
echo "  - Type a message to send it"
echo "  - Type 'cherry' or '1' to switch to Cherry"
echo "  - Type 'pompon' or '2' to switch to Pompon"
echo "  - Type 'switch' to toggle between characters"
echo "  - Type 'feed pompon' to simulate button 'Nourrir Pompon'"
echo "  - Type 'feed cherry' to simulate button 'Nourrir Cherry'"
echo "  - Type 'stats details' to simulate 'Voir détails'"
echo "  - Type 'stats promos' to simulate 'Mes promos'"
echo "  - Type 'stats fermer' to simulate 'Fermer'"
echo "  - Type 'quit' or 'exit' to stop"
echo
echo

# Helper: JSON-escape arbitrary text so it can be safely embedded
# into the curl -d JSON payload without breaking the syntax.
json_escape() {
  python - <<'EOF'
import json, sys
text = sys.stdin.read()
# json.dumps returns a JSON string literal, including surrounding quotes.
escaped = json.dumps(text)
print(escaped[1:-1])  # strip the outer quotes
EOF
}

send_request() {
  local body="$1"
  local product_id="$2"
  local type="${3:-manual}"

  # JSON-escape body to avoid invalid control characters / quotes
  local body_escaped
  body_escaped="$(printf '%s' "$body" | json_escape)"

  echo "============================================================"
  echo "Sending message: \"$body\""
  echo "Character: $CURRENT_CHARACTER (product_id=$product_id)"
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
                    \"text\": { \"body\": \"$body_escaped\" }$context_json
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

# Simulate an interactive button press (e.g. FEED_00002, FEED_00001)
send_button() {
  local button_id="$1"
  local title="$2"
  local type="${3:-button}"

  # JSON-escape id and title
  local button_id_escaped title_escaped
  button_id_escaped="$(printf '%s' "$button_id" | json_escape)"
  title_escaped="$(printf '%s' "$title" | json_escape)"

  echo "============================================================"
  echo "Simulating interactive button: id=\"$button_id\" title=\"$title\""
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
                    \"type\": \"interactive\",
                    \"interactive\": {
                      \"type\": \"button\",
                      \"button_reply\": {
                        \"id\": \"$button_id_escaped\",
                        \"title\": \"$title_escaped\"
                      }
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
  echo "Interactive button sent! Check your Flask server logs and WhatsApp behavior."
  echo
}

get_user_id_for_from_number() {
  python - <<EOF
from db.db import init_db, get_session, get_or_create_user

init_db()
session = get_session()
try:
    user = get_or_create_user(session, "$FROM_NUMBER")
    print(user.id)
finally:
    session.close()
EOF
}

switch_character() {
  local choice="$1"
  
  case "$choice" in
    cherry|1|Cherry|CHERRY)
      CURRENT_CHARACTER="Cherry"
      CURRENT_PRODUCT_ID="00001"
      echo "✅ Switched to Cherry (product_id=00001)"
      ;;
    pompon|2|Pompon|POMPON)
      CURRENT_CHARACTER="Pompon"
      CURRENT_PRODUCT_ID="00002"
      echo "✅ Switched to Pompon (product_id=00002)"
      ;;
    switch|s|Switch|SWITCH)
      if [ "$CURRENT_CHARACTER" = "Cherry" ]; then
        CURRENT_CHARACTER="Pompon"
        CURRENT_PRODUCT_ID="00002"
        echo "✅ Switched to Pompon (product_id=00002)"
      else
        CURRENT_CHARACTER="Cherry"
        CURRENT_PRODUCT_ID="00001"
        echo "✅ Switched to Cherry (product_id=00001)"
      fi
      ;;
    *)
      echo "❌ Unknown character. Use 'cherry', 'pompon', or 'switch'"
      return 1
      ;;
  esac
  return 0
}

# Interactive mode: prompt for message
if [ $# -eq 0 ]; then
  while true; do
    echo "[$CURRENT_CHARACTER] Enter a message (or 'cherry'/'pompon'/'switch' to change character, 'feed pompon'/'feed cherry' or 'stats details/promos/fermer' to simulate buttons, 'quit' to exit):"
    read -r message_body
    
    if [ -z "$message_body" ]; then
      echo "Message cannot be empty. Please try again."
      continue
    fi
    
    # Check for quit command
    if [ "$message_body" = "quit" ] || [ "$message_body" = "exit" ]; then
      echo "Exiting..."
      break
    fi
    
    # Check for character switch commands
    if [[ "$message_body" =~ ^(cherry|pompon|switch|1|2|s|Cherry|Pompon|Switch|CHERRY|POMPON|SWITCH)$ ]]; then
      switch_character "$message_body"
      echo
      continue
    fi

    # Check for feed selection button simulation
    if [[ "$message_body" =~ ^(feed[[:space:]]+pompon|feed[[:space:]]+Pompon|FEED_POMPON)$ ]]; then
      # FEED_00002 = Nourrir Pompon
      send_button "FEED_00002" "Nourrir Pompon" "feed"
      echo
      continue
    fi

    if [[ "$message_body" =~ ^(feed[[:space:]]+cherry|feed[[:space:]]+Cherry|FEED_CHERRY)$ ]]; then
      # FEED_00001 = Nourrir Cherry
      send_button "FEED_00001" "Nourrir Cherry" "feed"
      echo
      continue
    fi

    # Stats buttons simulation (Voir détails / Mes promos / Fermer)
    if [[ "$message_body" =~ ^(stats[[:space:]]+details|stats_details)$ ]]; then
      USER_ID="$(get_user_id_for_from_number)"
      send_button "stats_details_${USER_ID}" "Voir détails" "stats"
      echo
      continue
    fi

    if [[ "$message_body" =~ ^(stats[[:space:]]+promos|stats_promos)$ ]]; then
      USER_ID="$(get_user_id_for_from_number)"
      send_button "stats_promos_${USER_ID}" "Mes promos" "stats"
      echo
      continue
    fi

    if [[ "$message_body" =~ ^(stats[[:space:]]+fermer|stats[[:space:]]+close|stats_dismiss)$ ]]; then
      USER_ID="$(get_user_id_for_from_number)"
      send_button "stats_dismiss_${USER_ID}" "Fermer" "stats"
      echo
      continue
    fi
    
    # Send message with current character
    send_request "$message_body" "$CURRENT_PRODUCT_ID"
  done
else
  # Command-line mode: use first argument as message
  # Optional second argument for character: "cherry" or "pompon"
  if [ $# -ge 2 ]; then
    switch_character "$2"
    echo
  fi
  send_request "$1" "$CURRENT_PRODUCT_ID"
fi
