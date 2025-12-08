# Setting Up Cloudflare Tunnel for WhatsApp Webhooks

This guide will help you expose your local Flask server to the internet using Cloudflare Tunnel (cloudflared) so Meta's WhatsApp Cloud API can send webhooks to it.

## Why Cloudflare Tunnel?

- **Free tier with no warning pages** - WhatsApp can access media files directly
- **Stable and fast** - Reliable tunneling service
- **No account required** - Works immediately without signup
- **Better for media** - No interstitial pages blocking automated requests

## Prerequisites

- Flask server running on `localhost:5000`
- cloudflared installed (see installation steps below)

## Step 1: Install cloudflared

### Linux/WSL (Ubuntu/Debian)

```bash
# Download binary to local bin directory (no sudo required)
mkdir -p ~/.local/bin
curl -L --output ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x ~/.local/bin/cloudflared

# Add to PATH (add to ~/.bashrc for persistence)
export PATH="$HOME/.local/bin:$PATH"
```

### macOS

```bash
brew install cloudflared
```

### Windows

1. Download from: https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
2. Rename to `cloudflared.exe`
3. Add to PATH or run from the directory

### Verify Installation

```bash
cloudflared --version
```

## Step 2: Start Cloudflare Tunnel

```bash
cloudflared tunnel --url http://localhost:5000
```

This will:
- Create a public HTTPS URL (e.g., `https://abc123.trycloudflare.com`)
- Forward all requests to your local Flask server on port 5000
- Display the URL in the terminal output

**Important:** Keep this terminal window open. Closing it will stop the tunnel.

## Step 3: Note Your Cloudflare Tunnel URL

Look for output like:
```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
|  https://abc123-def456-ghi789.trycloudflare.com
+--------------------------------------------------------------------------------------------+
```

Copy the HTTPS URL.

## Step 4: Configure WhatsApp Webhook

1. Go to Meta Developer Console: https://developers.facebook.com/
2. Navigate to your WhatsApp app
3. Go to **Webhooks** → **WhatsApp Business Account**
4. Set:
   - **Callback URL**: `https://your-cloudflare-url.trycloudflare.com/whatsapp-webhook`
   - **Verify token**: Your `WHATSAPP_VERIFY_TOKEN` from `.env`
5. Click **Verify and Save**
6. Subscribe to the `messages` field

## Step 5: Set PUBLIC_BASE_URL for Media

For GIF/sticker sending to work, set the environment variable:

```bash
export PUBLIC_BASE_URL="https://your-cloudflare-url.trycloudflare.com"
```

Or add it to your `.env` file (if your app reads from there).

## Step 6: Test Your Webhook

1. Send a WhatsApp message to your WhatsApp Business number
2. Check your Flask server logs for incoming webhook requests
3. You should see the AI reply in your WhatsApp
4. GIFs and stickers should now work (unlike with ngrok free tier)

## Troubleshooting

### URL changes every time
- **Problem**: Cloudflare Tunnel URLs change when you restart the tunnel
- **Solution**: Update the webhook URL in Meta Developer Console each time, or use a named tunnel (requires Cloudflare account)

### Webhook not receiving requests
- Verify the webhook URL in Meta Developer Console matches your Cloudflare Tunnel URL exactly
- Make sure the URL ends with `/whatsapp-webhook`
- Check that your Flask server is running
- Verify cloudflared tunnel is running and showing the URL

### Media files not accessible
- Unlike ngrok free tier, Cloudflare Tunnel doesn't show warning pages
- Verify `PUBLIC_BASE_URL` is set correctly
- Test the media URL directly: `curl -I https://your-url.trycloudflare.com/gifs/your-file.mp4`

### Test webhook locally
You can test your webhook without Cloudflare Tunnel using the test script:
```bash
bash test_webhook.sh
```

## Advantages Over ngrok Free Tier

- ✅ No warning pages - WhatsApp can access media directly
- ✅ Better for automated services
- ✅ No account required
- ✅ Free tier is fully functional for development

## Quick Start Script

You can use the provided script to start the tunnel:
```bash
bash start_cloudflare_tunnel.sh
```

