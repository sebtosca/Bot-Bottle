# Webhook Troubleshooting Guide

## Issue: Receiving Messages But No Response

If you can send messages TO WhatsApp but don't receive responses when sending messages FROM WhatsApp, check the following:

## 1. Check Webhook Subscription in Meta Console

**Most Common Issue**: The webhook is not subscribed to the `messages` field.

### Steps:
1. Go to: https://developers.facebook.com/apps/
2. Select your app
3. Navigate to: **WhatsApp → Configuration**
4. Scroll to **Webhook** section
5. Click **Edit** or manage webhook
6. Under **Webhook fields** or **Subscribe to fields**, ensure:
   - ✅ `messages` is checked/subscribed
   - Optionally: `message_status`, `message_reactions`

If `messages` is not subscribed, Meta will not send webhook events when users send messages.

## 2. Check App Mode (Development vs Production)

**Development Mode Limitation**: In development mode, you can only receive webhooks for:
- Test messages sent from the Meta Developer Console dashboard
- Messages from test users (phone numbers added to test recipients list)

### To receive real user messages:
- You need to publish your app, OR
- Use the "Send test message" feature in Meta Console

### Check your app mode:
1. Go to Meta Developer Console → App Settings → Basic
2. Check if app is in "Development" or "Live" mode

## 3. Verify Webhook URL is Correct

The webhook URL must match exactly what's configured in Meta Console:

1. Check your current ngrok URL:
   ```bash
   curl http://localhost:4040/api/tunnels | python -m json.tool
   ```

2. Verify in Meta Console that the webhook URL matches:
   - Should be: `https://your-ngrok-url.ngrok-free.dev/whatsapp-webhook`
   - Must be HTTPS (not HTTP)
   - Must end with `/whatsapp-webhook`

## 4. Check Flask Server Logs

When you send a message, check your Flask server console for:

**Good signs:**
```
📥 Received webhook request
📨 Message received:
   From: 33684950535
   Type: text
📝 Generated reply: ...
📤 Sending text message...
✅ Text sent: wamid.xxx
```

**Bad signs:**
- No log output at all → Webhook not being called by Meta
- Error messages → Check the specific error

## 5. Test Webhook Manually

Test if the webhook endpoint is working:

```bash
python tests/test_webhook_text_message.py https://your-ngrok-url.ngrok-free.dev 33684950535
```

If this works but real messages don't, the issue is with Meta webhook subscription or app mode.

## 6. Check Webhook Delivery in Meta Console

1. Go to Meta Developer Console → WhatsApp → Configuration
2. Scroll to **Webhooks** section
3. Click **View webhook delivery logs** or similar
4. Check if webhook events are being sent and their status

## 7. Verify Recipient Opt-In

For test numbers:
- Recipient must be added to test recipients list in Meta Console
- Recipient must have sent a message to your business number first

## Quick Diagnostic Commands

```bash
# 1. Check webhook verification
python scripts/check_webhook_status.py

# 2. Test webhook with sample payload
python tests/test_webhook_text_message.py https://your-ngrok-url.ngrok-free.dev 33684950535

# 3. Check if Flask server is receiving requests
# (Watch the Flask server console when sending a message)
```

## Common Solutions

### Solution 1: Subscribe to Messages Field
- Go to Meta Console → WhatsApp → Configuration → Webhooks
- Ensure `messages` field is subscribed

### Solution 2: Use Test Message Feature
- In Meta Console → WhatsApp → API Setup
- Use "Send test message" to test webhook without publishing app

### Solution 3: Check ngrok URL Changed
- If you restarted ngrok, the URL changed
- Update webhook URL in Meta Console to new ngrok URL

### Solution 4: Restart Flask Server
- Stop Flask server (Ctrl+C)
- Restart: `python endpoint/endpoint.py`
- Ensure you see the startup messages

## Still Not Working?

1. **Check Flask server logs** - Look for any error messages
2. **Check Meta webhook delivery logs** - See if Meta is sending events
3. **Verify webhook subscription** - Ensure `messages` is subscribed
4. **Test with sample payload** - Use the test script to verify endpoint works
5. **Check app mode** - Development mode has limitations

