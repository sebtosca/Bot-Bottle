# Webhook Troubleshooting Guide

## Issue: Messages Not Being Received on WhatsApp

### Root Cause Found ✅

The `process_whatsapp_message()` function in `endpoint/webhook/message_processor.py` was a **placeholder** that only logged warnings and did not actually process messages or send responses.

### What Was Happening

1. ✅ Webhook receives message from WhatsApp
2. ✅ Message is parsed correctly
3. ✅ Message is enqueued successfully
4. ✅ Worker picks up message from queue
5. ✅ Worker calls `process_whatsapp_message()`
6. ❌ **But `process_whatsapp_message()` was just a placeholder doing NOTHING!**

### Fix Applied

The full message processing logic has been implemented in `endpoint/webhook/message_processor.py`. It now:

- Gets/creates user and bottle
- Handles different message types (text, emoji, image, etc.)
- Processes game logic (feeding, fullness, stickers)
- Generates LLM replies
- Sends WhatsApp responses
- Handles character switching
- Handles receipt verification
- Handles stats requests

### Verification Steps

1. **Check Logs**: Look for these log messages:
   - `"Processing WhatsApp message"` - Message received
   - `"Message processed successfully"` - Processing completed
   - `"Message processor not yet implemented"` - **This should NOT appear anymore**

2. **Test the Flow**:
   ```bash
   # Send a test message to your WhatsApp number
   # Check logs for processing messages
   # Verify response is sent
   ```

3. **Common Issues to Check**:

   **a) Cloudflare Tunnel**
   - Ensure tunnel is running: `cloudflared tunnel --url http://localhost:5000`
   - Verify webhook URL in Meta dashboard points to your tunnel URL
   - Test webhook verification: `curl "https://your-tunnel-url/whatsapp-webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test"`

   **b) Environment Variables**
   - `PUBLIC_BASE_URL` - Must be your Cloudflare tunnel URL (e.g., `https://your-tunnel-url.trycloudflare.com`)
   - `WHATSAPP_ACCESS_TOKEN` - Valid access token
   - `WHATSAPP_PHONE_NUMBER_ID` - Valid phone number ID
   - `DATABASE_URL` - Valid database connection

   **c) Worker Status**
   - Check logs for: `"In-memory queue worker started for local development"`
   - If using Azure Service Bus, ensure connection string is set

   **d) Message Processing Errors**
   - Check logs for exceptions during processing
   - Verify database connection
   - Verify LLM API key (Mistral) if using LLM features

### Testing

1. **Send a text message** to your WhatsApp number
2. **Check application logs** for:
   ```
   INFO: Processing WhatsApp message
   INFO: Message processed successfully
   ```
3. **Verify response** is received on WhatsApp

### If Still Not Working

1. **Check Logs**: Look for error messages in the logs
2. **Verify Cloudflare Tunnel**: Ensure it's running and accessible
3. **Test Webhook**: Use Meta's webhook testing tool
4. **Check Database**: Ensure database is accessible and initialized
5. **Verify API Keys**: Ensure all required API keys are set

### Cloudflare Tunnel Setup

```bash
# Install cloudflared (if not installed)
# Windows: Download from https://github.com/cloudflare/cloudflared/releases
# Linux/Mac: brew install cloudflared or download binary

# Start tunnel
cloudflared tunnel --url http://localhost:5000

# Copy the HTTPS URL (e.g., https://xxxxx.trycloudflare.com)
# Use this URL in:
# 1. Meta webhook configuration
# 2. PUBLIC_BASE_URL environment variable
```

### Environment Variables Checklist

```bash
# Required
DATABASE_URL=postgresql+psycopg2://...
WHATSAPP_ACCESS_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
PUBLIC_BASE_URL=https://your-tunnel-url.trycloudflare.com

# Optional (for LLM features)
MISTRAL_API_KEY=your_key
MISTRAL_MODEL_NAME=ministral-3b

# Optional (for production)
REDIS_URL=redis://...  # For idempotency
AZURE_SERVICE_BUS_CONNECTION_STRING=...  # For queue
```
