# WhatsApp Webhook Testing Guide

## Current Status

✅ **LLM (Mistral AI)**: Working  
✅ **WhatsApp Cloud API**: Working  
✅ **Webhook Endpoint**: Code updated with error handling  
⚠️ **Flask Server**: Needs restart to pick up changes

## Issue Found

The webhook has been updated with:
- Error handling for LLM failures
- Better phone number formatting
- Improved error logging
- Detailed diagnostics when LLM fails

## Steps to Fix

### 1. Restart Your Flask Server

**Stop the current Flask server** (Ctrl+C in the terminal where it's running), then restart it:

```bash
python endpoint/endpoint.py
```

You should see:
```
Starting BotBottle Flask server...
Health check: http://localhost:5000/health
WhatsApp webhook: http://localhost:5000/whatsapp-webhook
```

### 2. Test the Webhook

Once the server is restarted, test it:

```bash
python tests/test_webhook_text_message.py https://dragonfly-interfilar-magaly.ngrok-free.dev 33684950535
```

This should now return:
- ✅ Status 200
- ✅ A message ID
- ✅ A reply text

### 3. Test with Real WhatsApp Message

1. From your phone (`+33684950535`), send a message to your WhatsApp Business number
2. Check your Flask server logs - you should see:
   - Message received
   - Reply generated
   - Message sent
3. You should receive a reply in WhatsApp

## Troubleshooting

### If webhook still fails after restart:

1. **Check Flask server logs** for error messages
2. **Verify credentials**:
   ```bash
   python scripts/check_whatsapp_credentials.py
   ```
3. **Test LLM and WhatsApp separately**:
   ```bash
   python scripts/debug_webhook.py
   ```

### If messages are received but no reply:

1. **Check webhook subscription** in Meta Console:
   - Go to WhatsApp → Configuration → Webhooks
   - Ensure `messages` field is subscribed
2. **Check recipient opt-in**:
   - Recipient must have sent a message to your business number first
3. **Check Flask server logs** for processing errors

### If ngrok URL changed:

1. Get new URL: Check ngrok terminal or visit http://localhost:4040
2. Update Meta Console webhook URL to new ngrok URL
3. Re-verify the webhook

## Quick Test Commands

```bash
# 1. Check credentials
python scripts/check_whatsapp_credentials.py

# 2. Test LLM and WhatsApp API
python scripts/debug_webhook.py

# 3. Test webhook endpoint
python tests/test_webhook_text_message.py https://your-ngrok-url.ngrok-free.dev 33684950535

# 4. Test webhook verification
python tests/test_whatsapp_webhook.py https://your-ngrok-url.ngrok-free.dev
```

## Expected Behavior

When working correctly:
1. ✅ Webhook receives message from Meta
2. ✅ Message is parsed correctly
3. ✅ LLM generates reply
4. ✅ Reply is sent via WhatsApp Cloud API
5. ✅ User receives reply in WhatsApp

## Next Steps

After confirming text messages work:
- Test sticker sending
- Test GIF sending
- Verify database logging (if DATABASE_URL is set)

