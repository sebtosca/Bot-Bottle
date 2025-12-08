"""Monitor webhook requests in real-time.

This script checks ngrok for incoming webhook requests and displays them.
Run this in a separate terminal to see when Meta sends webhooks.
"""

import time
import requests
import json
from datetime import datetime

def monitor_webhooks(check_interval=2):
    """Monitor ngrok for webhook requests."""
    print("=" * 60)
    print("🔍 Webhook Monitor")
    print("=" * 60)
    print("Monitoring ngrok for incoming webhook requests...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()
    
    last_count = 0
    
    try:
        while True:
            try:
                resp = requests.get("http://localhost:4040/api/requests/http", timeout=2)
                data = resp.json()
                reqs = data.get("requests", [])
                
                webhook_reqs = [r for r in reqs if '/whatsapp-webhook' in r.get('request', {}).get('uri', '')]
                current_count = len(webhook_reqs)
                
                if current_count > last_count:
                    new_reqs = webhook_reqs[- (current_count - last_count):]
                    for req in new_reqs:
                        method = req.get('request', {}).get('method', 'N/A')
                        uri = req.get('request', {}).get('uri', 'N/A')
                        status = req.get('response', {}).get('status', 'N/A')
                        timestamp = req.get('started_at', datetime.now().isoformat())
                        
                        print(f"[{timestamp}] {method} {uri}")
                        print(f"  Status: {status}")
                        
                        # Show request body preview for POST requests
                        if method == "POST":
                            body = req.get('request', {}).get('body', '')
                            if body:
                                try:
                                    body_data = json.loads(body)
                                    if 'entry' in body_data:
                                        entry = body_data.get('entry', [])
                                        if entry and 'changes' in entry[0]:
                                            value = entry[0]['changes'][0].get('value', {})
                                            messages = value.get('messages', [])
                                            if messages:
                                                msg = messages[0]
                                                from_num = msg.get('from', 'N/A')
                                                msg_type = msg.get('type', 'N/A')
                                                print(f"  From: {from_num}, Type: {msg_type}")
                                except:
                                    pass
                        print()
                    
                    last_count = current_count
                
                time.sleep(check_interval)
                
            except requests.exceptions.RequestException:
                print("⚠️  Could not connect to ngrok API. Is ngrok running?")
                time.sleep(5)
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped.")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == "__main__":
    monitor_webhooks()

