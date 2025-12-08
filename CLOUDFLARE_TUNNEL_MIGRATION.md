# Migrating from ngrok to Cloudflare Tunnel

This guide helps you switch from ngrok to Cloudflare Tunnel to enable GIF/sticker sending.

## Why Switch?

- **ngrok free tier**: Shows warning pages that block WhatsApp from accessing media files
- **Cloudflare Tunnel free tier**: No warning pages - WhatsApp can access media directly

## Quick Migration Steps

### 1. Install Cloudflare Tunnel

See [SETUP_CLOUDFLARE_TUNNEL.md](SETUP_CLOUDFLARE_TUNNEL.md) for installation instructions.

### 2. Stop ngrok

Stop your current ngrok tunnel (Ctrl+C in the ngrok terminal).

### 3. Start Cloudflare Tunnel

```bash
bash start_cloudflare_tunnel.sh
```

Or manually:
```bash
cloudflared tunnel --url http://localhost:5000
```

### 4. Note Your New URL

Copy the Cloudflare Tunnel URL (e.g., `https://abc123.trycloudflare.com`)

### 5. Update WhatsApp Webhook URL

1. Go to Meta Developer Console: https://developers.facebook.com/
2. Navigate to your WhatsApp app → **Webhooks** → **WhatsApp Business Account**
3. Update **Callback URL** to: `https://your-cloudflare-url.trycloudflare.com/whatsapp-webhook`
4. Click **Verify and Save**

### 6. Update Environment Variables

Set `PUBLIC_BASE_URL` to your Cloudflare Tunnel URL:

```bash
export PUBLIC_BASE_URL="https://your-cloudflare-url.trycloudflare.com"
```

Or add to your `.env` file if your app reads from there.

### 7. Test

1. Send a WhatsApp message
2. Verify you receive a reply
3. Verify GIFs/stickers are sent (this should now work!)

## What Changed?

- **Tunneling service**: ngrok → Cloudflare Tunnel
- **URL format**: `*.ngrok-free.app` → `*.trycloudflare.com`
- **Media access**: Now works without warning pages!

## Rollback

If you need to go back to ngrok:
1. Stop Cloudflare Tunnel
2. Start ngrok: `ngrok http 5000`
3. Update webhook URL back to ngrok URL
4. Note: GIF/sticker sending will stop working again due to warning page

