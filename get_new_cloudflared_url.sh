#!/bin/bash
# Script simple pour obtenir une nouvelle URL de cloudflared

echo "Arrêt de cloudflared..."
pkill cloudflared 2>/dev/null
sleep 2

echo "Démarrage de cloudflared..."
echo ""
echo "=== ATTENDEZ QUE L'URL APPARAISSE ==="
echo ""

cloudflared tunnel --url http://localhost:5000 2>&1 | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1 | while read url; do
    echo ""
    echo "=== URL TROUVÉE ==="
    echo "$url"
    echo ""
    echo "Mettez à jour votre .env avec:"
    echo "PUBLIC_BASE_URL=$url"
    echo ""
done

