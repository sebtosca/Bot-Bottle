# WhatsApp Cloud API Webhook Setup & Testing Guide

## Prerequisites Checklist

Before testing, ensure you have:

- [x] **WhatsApp Cloud API Credentials** (already configured):
  - `WHATSAPP_ACCOUNT_ID` (or `WHATSAPP_BUSINESS_ID`)
  - `WHATSAPP_PHONE_NUMBER_ID` (or `WHATSAPP_NUMBER`)
  - `WHATSAPP_ACCESS_TOKEN` (or `WHATSAPP_TOKEN`)
  - `WHATSAPP_VERIFY_TOKEN` (set to `AIARTPROGRAM`)

- [ ] **Flask Server Running**: Your endpoint server must be running
- [ ] **ngrok Running**: To expose your local server to the internet
- [ ] **Webhook Configured in Meta Developer Console**: Set the webhook URL and verify token

## Step-by-Step Testing

### Step 1: Start Your Flask Server

```bash
python endpoint/endpoint.py
```

You should see:
```
Starting BotBottle Flask server...
Health check: http://localhost:5000/health
WhatsApp webhook: http://localhost:5000/whatsapp-webhook
```

### Step 2: Start ngrok (if testing locally)

```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

### Step 3: Test Webhook Locally (Before Meta Configuration)

Test the webhook endpoint directly:

```bash
# Test webhook verification
python tests/test_whatsapp_webhook.py http://localhost:5000

# Or if using ngrok:
python tests/test_whatsapp_webhook.py https://your-ngrok-url.ngrok-free.app
```

This will test:
1. Webhook verification (GET request)
2. Text message handling (POST request)
3. Sticker message handling (POST request)

### Step 4: Configure Webhook in Meta Developer Console

1. Go to: https://developers.facebook.com/apps/
2. Select your app
3. Navigate to: **WhatsApp → Configuration**
4. Scroll to **Webhook** section
5. Click **Edit** or **Set up webhook**
6. Enter:
   - **Callback URL**: `https://your-ngrok-url.ngrok-free.app/whatsapp-webhook`
   - **Verify token**: `AIARTPROGRAM` (or your `WHATSAPP_VERIFY_TOKEN` value)
7. Click **Verify and save**
8. Under **Webhook fields**, subscribe to:
   - ✅ `messages` (required)
   - Optionally: `message_status`, `message_reactions`, etc.

### Step 5: Test with Real WhatsApp Message

1. From your test phone number (`+33684950535`), send a message to your WhatsApp Business number
2. Check your Flask server logs for:
   - ✅ "Webhook verified successfully" (if Meta verifies)
   - ✅ Message processing logs
   - ✅ Response sending logs

3. You should receive a reply in WhatsApp

## Troubleshooting

### Webhook Verification Fails

- **Check verify token**: Ensure `WHATSAPP_VERIFY_TOKEN` in `.env` matches what you entered in Meta Console
- **Check server is running**: The webhook endpoint must be accessible
- **Check ngrok URL**: Make sure ngrok is running and URL is correct

### Messages Not Received

- **Check webhook subscription**: Ensure `messages` field is subscribed in Meta Console
- **Check recipient opt-in**: Recipient must have sent a message to your business number first
- **Check server logs**: Look for errors in Flask server output
- **Check Meta webhook logs**: Go to Meta Developer Console → WhatsApp → Webhooks to see delivery status

### Server Not Responding

- **Check Flask server**: Ensure `python endpoint/endpoint.py` is running
- **Check port**: Default is 5000, make sure nothing else is using it
- **Check ngrok**: Ensure ngrok tunnel is active and pointing to correct port

## Quick Test Commands

```bash
# 1. Check credentials
python scripts/check_whatsapp_credentials.py

# 2. Test sending a message
python tests/test_whatsapp_cloud_api.py +33684950535

# 3. Test webhook locally
python tests/test_whatsapp_webhook.py http://localhost:5000

# 4. Test webhook via ngrok
python tests/test_whatsapp_webhook.py https://your-ngrok-url.ngrok-free.app
```

## Webhook Endpoints

- **New endpoint**: `/whatsapp-webhook` (GET for verification, POST for messages)

