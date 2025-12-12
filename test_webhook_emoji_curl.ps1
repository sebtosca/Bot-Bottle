# Test webhook script to send an emoji using curl
# Usage:
#   .\test_webhook_emoji_curl.ps1

$WEBHOOK_URL = if ($env:WEBHOOK_URL) { $env:WEBHOOK_URL } else { "http://localhost:5000/whatsapp-webhook" }
$FROM_NUMBER = if ($env:FROM_NUMBER) { $env:FROM_NUMBER } else { "33684950535" }

Write-Host "============================================================"
Write-Host "WhatsApp Webhook Emoji Test (curl)"
Write-Host "============================================================"
Write-Host "Using webhook URL: $WEBHOOK_URL"
Write-Host "Simulated from number: $FROM_NUMBER"
Write-Host "Sending emoji: 😀"
Write-Host "============================================================"
Write-Host ""

$timestamp = Get-Date -UFormat %s
$randomId = Get-Random

# Use curl with UTF-8 encoding
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
                "text": { "body": "😀" }
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

# Save to temp file with UTF-8 encoding
$tempFile = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tempFile, $jsonPayload, [System.Text.Encoding]::UTF8)

try {
    # Use curl if available, otherwise use Invoke-WebRequest
    if (Get-Command curl -ErrorAction SilentlyContinue) {
        curl -i -X POST "$WEBHOOK_URL" -H "Content-Type: application/json; charset=utf-8" --data-binary "@$tempFile"
    } else {
        $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonPayload)
        $response = Invoke-WebRequest -Uri $WEBHOOK_URL -Method POST -Body $utf8Bytes -ContentType "application/json; charset=utf-8" -UseBasicParsing
        Write-Host "Status Code: $($response.StatusCode)"
        Write-Host "Response: $($response.Content)"
    }
    Write-Host ""
    Write-Host "✅ Emoji sent successfully!"
} catch {
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)"
} finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Check your Flask server logs and your WhatsApp for replies."
Write-Host ""
