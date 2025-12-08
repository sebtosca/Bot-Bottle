#!/usr/bin/env bash

# Check if Flask server is running on port 5000

echo "Checking Flask server status..."
echo

# Check if port 5000 is in use
if lsof -i :5000 >/dev/null 2>&1 || netstat -an 2>/dev/null | grep -q ":5000.*LISTEN"; then
    echo "✅ Port 5000 is in use"
    echo
    echo "Processes using port 5000:"
    lsof -i :5000 2>/dev/null || netstat -ano | grep :5000 2>/dev/null || echo "   (Cannot list processes)"
    echo
else
    echo "❌ Port 5000 is NOT in use"
    echo "   Flask server is not running"
    echo
    echo "To start Flask server, run:"
    echo "   python endpoint/endpoint.py"
    exit 1
fi

# Test health endpoint
echo "Testing Flask server health endpoint..."
if curl -s http://localhost:5000/health >/dev/null 2>&1; then
    echo "✅ Flask server is responding"
    response=$(curl -s http://localhost:5000/health)
    echo "   Response: $response"
    echo
    echo "✅ Flask server is ready!"
    echo
    echo "You can now:"
    echo "  1. Run test script: bash test_webhook.sh"
    echo "  2. Send real WhatsApp messages"
    echo
else
    echo "❌ Flask server is not responding"
    echo "   Port 5000 is in use but server is not responding"
    echo "   You may need to restart the Flask server"
    exit 1
fi

