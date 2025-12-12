# Test webhook script to send an emoji
# Usage:
#   .\test_webhook_emoji.ps1
#   $env:WEBHOOK_URL="http://localhost:5000/whatsapp-webhook"; .\test_webhook_emoji.ps1

$WEBHOOK_URL = if ($env:WEBHOOK_URL) { $env:WEBHOOK_URL } else { "http://localhost:5000/whatsapp-webhook" }
$FROM_NUMBER = if ($env:FROM_NUMBER) { $env:FROM_NUMBER } else { "33684950535" }

# The happy face emoji 😀
$EMOJI = "😀"

Write-Host "============================================================"
Write-Host "WhatsApp Webhook Emoji Test"
Write-Host "============================================================"
Write-Host "Using webhook URL: $WEBHOOK_URL"
Write-Host "Simulated from number: $FROM_NUMBER"
Write-Host "Sending emoji: $EMOJI"
Write-Host "============================================================"
Write-Host ""

$timestamp = [int][double]::Parse((Get-Date -UFormat %s))
$randomId = Get-Random

# Create JSON payload with proper UTF-8 encoding
$jsonPayload = @"
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "test_waba",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "contacts": [
              {
                "profile": { "name": "Test User" },
                "wa_id": "$FROM_NUMBER"
              }
            ],
            "messages": [
              {
                "from": "$FROM_NUMBER",
                "id": "wamid.test.emoji.$randomId",
                "timestamp": "$timestamp",
                "type": "text",
                "text": { "body": "$EMOJI" }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
"@

# Convert to UTF-8 bytes and send
$utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonPayload)

try {
    $response = Invoke-WebRequest -Uri $WEBHOOK_URL -Method POST -Body $utf8Bytes -ContentType "application/json; charset=utf-8" -UseBasicParsing
    Write-Host ""
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Response: $($response.Content)"
    Write-Host ""
    Write-Host "✅ Emoji sent successfully!"
} catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody"
    }
    Write-Host ""
    Write-Host "⚠️  Check if your Flask server is running on $WEBHOOK_URL"
}

Write-Host ""
Write-Host "Check your Flask server logs and your WhatsApp for replies."
Write-Host ""
