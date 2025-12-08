# WhatsApp Message Delivery Troubleshooting Guide

## Problem: Messages Show as "Sent Successfully" but Aren't Delivered

If your WhatsApp messages show as sent successfully (return a message ID) but you don't receive them, this guide will help you diagnose and fix the issue.

## Common Causes

### 1. Recipient Not in Allowed List (Most Common)

**Symptom:** API returns 200 OK with message ID, but message never arrives.

**Cause:** In test mode, WhatsApp only allows sending messages to phone numbers that are explicitly added to your allowed recipients list.

**Solution:**

1. Go to [Meta Developer Console](https://developers.facebook.com/)
2. Navigate to your WhatsApp app
3. Click on **API Setup** (or **WhatsApp** → **API Setup**)
4. Scroll down to **"Add a recipient phone number"** section
5. Enter your phone number in E.164 format (e.g., `+33684950535`)
6. Click **Add** or **Save**
7. Wait a few seconds for the change to take effect
8. Try sending a message again

**Note:** In test mode, you can only send messages to numbers in this list. Once your app is approved for production, this restriction is removed.

### 2. Invalid Phone Number Format

**Symptom:** Error code 131026 or "invalid recipient" error.

**Cause:** Phone number is not in E.164 format.

**Solution:**

Phone numbers must be in **E.164 format**:
- Start with `+` followed by country code
- Example: `+33684950535` (France)
- Example: `+14155552671` (USA)
- Example: `+447911123456` (UK)

**Common mistakes:**
- Missing `+` prefix: `33684950535` ❌ → `+33684950535` ✅
- Including spaces: `+33 684 950 535` ❌ → `+33684950535` ✅
- Including dashes: `+33-684-950-535` ❌ → `+33684950535` ✅
- Including parentheses: `+33 (684) 950-535` ❌ → `+33684950535` ✅

### 3. Rate Limiting

**Symptom:** Error code 131048 or "rate limit exceeded" error.

**Cause:** Too many messages sent too quickly.

**Solution:**
- Wait a few minutes before sending more messages
- WhatsApp has rate limits to prevent spam
- In test mode, limits are stricter

### 4. Invalid Access Token

**Symptom:** Error code 401 or 403, "authentication error".

**Cause:** Access token is expired, invalid, or missing.

**Solution:**
1. Check your `.env` file has `WHATSAPP_ACCESS_TOKEN` set
2. Verify the token is correct in Meta Developer Console
3. Generate a new token if needed:
   - Go to Meta Developer Console → Your App → Settings → Basic
   - Copy the **Access Token** (or generate a new one)

### 5. Invalid Phone Number ID

**Symptom:** Error code 404 or "phone number ID not found".

**Cause:** `WHATSAPP_PHONE_NUMBER_ID` is incorrect or missing.

**Solution:**
1. Check your `.env` file has `WHATSAPP_PHONE_NUMBER_ID` set
2. Find your Phone Number ID in Meta Developer Console:
   - Go to WhatsApp → API Setup
   - Look for "Phone number ID" or "From" field
   - Copy the ID (it's a long number)

## Diagnostic Tools

### Test Message Delivery Script

Use the diagnostic script to test message sending:

```bash
python test_message_delivery.py +33684950535
```

This script will:
- Validate phone number format
- Check configuration (access token, phone number ID)
- Attempt to send a test message
- Provide specific error messages and solutions

### Check Flask Server Logs

When a message fails to send, check your Flask server logs for detailed error information:

```bash
# Look for error messages like:
❌ Error sending message: WhatsApp Cloud API error: ...
⚠️  RECIPIENT NOT IN ALLOWED LIST
```

The logs will show:
- Error codes
- Specific error messages
- Full API responses (for debugging)

## Step-by-Step Troubleshooting

### Step 1: Verify Phone Number Format

```bash
python test_message_delivery.py +YOUR_PHONE_NUMBER
```

The script will validate the format and tell you if it's correct.

### Step 2: Check if Recipient is in Allowed List

1. Go to Meta Developer Console
2. Navigate to your WhatsApp app → API Setup
3. Check the "Add a recipient phone number" section
4. Verify your number is listed there
5. If not, add it and wait a few seconds

### Step 3: Test Message Sending

```bash
python test_message_delivery.py +YOUR_PHONE_NUMBER "Test message"
```

### Step 4: Check Error Messages

If the message fails, the script will show:
- Specific error code
- Detailed error message
- Step-by-step solution

### Step 5: Check Flask Server Logs

If using the webhook, check your Flask server output for detailed error information.

## Error Code Reference

| Error Code | Meaning | Solution |
|------------|---------|----------|
| 131030 | Recipient not in allowed list | Add number to allowed list in Meta Developer Console |
| 131026 | Invalid phone number format | Use E.164 format: +[country code][number] |
| 131047 | Message failed to send | Check recipient number and try again |
| 131048 | Rate limit exceeded | Wait a few minutes before sending more messages |
| 401 | Authentication error | Check access token |
| 403 | Forbidden | Check permissions and access token |
| 404 | Not found | Check phone number ID |

## Testing Mode vs Production Mode

### Test Mode (Default)
- **Restriction:** Can only send to numbers in allowed list
- **Limit:** Stricter rate limits
- **Use case:** Development and testing

### Production Mode
- **Restriction:** Can send to any number (after user opts in)
- **Limit:** Higher rate limits
- **Use case:** Live application

**To move to production:**
1. Complete app review process in Meta Developer Console
2. Submit your app for review
3. Once approved, restrictions are lifted

## Quick Checklist

Before reporting an issue, verify:

- [ ] Phone number is in E.164 format (`+[country][number]`)
- [ ] Phone number is added to allowed list in Meta Developer Console
- [ ] `WHATSAPP_ACCESS_TOKEN` is set and valid
- [ ] `WHATSAPP_PHONE_NUMBER_ID` is set and correct
- [ ] Flask server is running
- [ ] Webhook URL is configured correctly (if using webhooks)
- [ ] You've waited a few seconds after adding recipient to allowed list

## Getting Help

If you've tried all the above and still have issues:

1. Run the diagnostic script: `python test_message_delivery.py +YOUR_NUMBER`
2. Check Flask server logs for detailed error messages
3. Note the specific error code and message
4. Check [WhatsApp Cloud API documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
5. Check Meta Developer Console for any warnings or errors

## Related Documentation

- [WhatsApp Cloud API Setup](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Meta Developer Console](https://developers.facebook.com/)
- [E.164 Phone Number Format](https://en.wikipedia.org/wiki/E.164)

