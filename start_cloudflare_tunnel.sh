#!/usr/bin/env bash

# Start Cloudflare Tunnel for BotBottle Flask server
# This script starts cloudflared to expose localhost:5000 to the internet

echo "============================================================"
echo "Starting Cloudflare Tunnel"
echo "============================================================"
echo

# Check if cloudflared is available
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found in PATH"
    echo
    echo "Installation options:"
    echo "  1. Linux/WSL:"
    echo "     mkdir -p ~/.local/bin"
    echo "     curl -L --output ~/.local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    echo "     chmod +x ~/.local/bin/cloudflared"
    echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo
    echo "  2. macOS:"
    echo "     brew install cloudflared"
    echo
    echo "  3. See SETUP_CLOUDFLARE_TUNNEL.md for more options"
    exit 1
fi

# Check if Flask server is running
echo "Checking if Flask server is running on port 5000..."
if ! lsof -i :5000 >/dev/null 2>&1 && ! netstat -an 2>/dev/null | grep -q ":5000.*LISTEN"; then
    echo "⚠️  Port 5000 is not in use"
    echo "   Flask server may not be running"
    echo
    echo "Start Flask server in another terminal:"
    echo "   python -m endpoint.endpoint"
    echo
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ Flask server appears to be running on port 5000"
fi

echo
echo "============================================================"
echo "Starting Cloudflare Tunnel..."
echo "============================================================"
echo "This will create a public HTTPS URL that forwards to localhost:5000"
echo "Keep this terminal open to maintain the tunnel"
echo
echo "Press Ctrl+C to stop the tunnel"
echo "============================================================"
echo

# Start cloudflared tunnel
cloudflared tunnel --url http://localhost:5000

