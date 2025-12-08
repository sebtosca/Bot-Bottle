# Troubleshooting Guide

## Common Issues and Solutions

### Webhook Not Receiving Messages

**Symptoms:**
- Messages sent to WhatsApp Business number
- No AI replies received
- Flask server logs show no incoming webhook requests

**Solutions:**

1. **Check Webhook Configuration in Meta Developer Console**
   - Go to: https://developers.facebook.com/
   - Navigate to your WhatsApp app → Webhooks → WhatsApp Business Account
   - Verify Callback URL matches your ngrok URL: `https://your-url.ngrok-free.app/whatsapp-webhook`
   - Verify token matches your `WHATSAPP_VERIFY_TOKEN` from `.env`
   - Ensure `messages` field is subscribed

2. **Check ngrok Status**
   - Verify ngrok is running: `ngrok http 5000`
   - Check ngrok web interface: `http://localhost:4040`
   - Verify ngrok URL hasn't changed (free URLs change on restart)

3. **Check Flask Server**
   - Ensure Flask server is running on port 5000
   - Check server logs for errors
   - Test health endpoint: `curl http://localhost:5000/health`

4. **Verify App Mode**
   - Development mode: Only test webhooks from dashboard work
   - Live mode: Real user messages trigger webhooks
   - To receive real messages, app must be in Live mode with business verification

### Messages Received But No Reply

**Symptoms:**
- Webhook receives message (logs show incoming request)
- No reply sent back
- Flask server logs show errors

**Solutions:**

1. **Check LLM Configuration**
   - Verify `MISTRAL_API_KEY` is set in `.env`
   - Test LLM directly: `python test_ai_direct.py`
   - Check Flask logs for LLM errors

2. **Check WhatsApp Cloud API Credentials**
   - Verify `WHATSAPP_ACCESS_TOKEN` is valid
   - Verify `WHATSAPP_PHONE_NUMBER_ID` is correct
   - Test credentials: `python scripts/check_whatsapp_credentials.py`

3. **Check Recipient Number**
   - Development mode: Number must be in test recipient list
   - Go to WhatsApp → API Setup → Add recipient phone number
   - Verify recipient number is added and verified

4. **Check Database**
   - Verify `DATABASE_URL` is set in `.env`
   - Check database connection: `python tests/test_db.py`
   - Ensure stickers are loaded: `python scripts/load_stickers.py`

### Error: "Recipient not in allowed list"

**Solution:**
- Go to Meta Developer Console → WhatsApp → API Setup
- Under "Add a recipient phone number", add your test number
- Save and try again
- In development mode, only numbers in this list can receive messages

### Error: "Access token expired"

**Solution:**
- Generate new access token from Meta Developer Console
- Update `WHATSAPP_ACCESS_TOKEN` in `.env`
- Restart Flask server

### Error: "LLM returned None"

**Symptoms:**
- Flask logs show: "Generated reply is empty, using fallback"
- No reply sent

**Solutions:**
1. Check Mistral AI API key is valid
2. Check Mistral AI API status: https://console.mistral.ai/
3. Verify model name in config
4. Check Flask logs for detailed Mistral AI API response

### Stickers Not Sending

**Symptoms:**
- Text messages work
- Stickers not received

**Solutions:**
1. Verify stickers are loaded in database: `python scripts/load_stickers.py`
2. Check sticker files exist in `stickers/` directory
3. Verify sticker URLs are accessible via ngrok
4. Check Flask logs for sticker selection and sending errors

## Debugging Tools

### Test Webhook Locally
```bash
bash test_webhook.sh
```

### Test AI Directly
```bash
python test_ai_direct.py
```

### Check WhatsApp Credentials
```bash
python scripts/check_whatsapp_credentials.py
```

### Check Webhook Status
```bash
python scripts/check_webhook_status.py
```

### Monitor Webhooks
```bash
python scripts/monitor_webhooks.py
```

## Quick Checklist

When troubleshooting, verify:
- [ ] Flask server is running
- [ ] ngrok tunnel is active
- [ ] Webhook URL in Meta Console matches ngrok URL
- [ ] Verify token matches `.env` file
- [ ] `messages` field is subscribed
- [ ] `MISTRAL_API_KEY` is set in `.env`
- [ ] WhatsApp credentials are valid
- [ ] Recipient number is in allowed list (dev mode)
- [ ] Database is configured and accessible
