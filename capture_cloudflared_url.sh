#!/bin/bash
# Script pour capturer l'URL de cloudflared au démarrage

echo "============================================================"
echo "CAPTURE URL CLOUDFLARE TUNNEL"
echo "============================================================"
echo ""
echo "Ce script va:"
echo "1. Arrêter cloudflared s'il est en cours d'exécution"
echo "2. Redémarrer cloudflared et capturer l'URL"
echo ""
read -p "Continuer? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé."
    exit 1
fi

echo ""
echo "🛑 Arrêt de cloudflared..."
pkill cloudflared 2>/dev/null
sleep 2

echo "🚀 Démarrage de cloudflared..."
echo ""
echo "============================================================"
echo "ATTENDEZ QUE L'URL APPARAISSE CI-DESSOUS"
echo "============================================================"
echo ""

# Démarrer cloudflared et capturer l'URL
cloudflared tunnel --url http://localhost:5000 2>&1 | tee /tmp/cloudflared_output.log | while IFS= read -r line; do
    echo "$line"
    
    # Chercher l'URL dans la ligne
    if echo "$line" | grep -qE 'https://[a-z0-9-]+\.trycloudflare\.com'; then
        url=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | head -1)
        if [ ! -z "$url" ]; then
            echo ""
            echo "============================================================"
            echo "✅ URL TROUVÉE: $url"
            echo "============================================================"
            echo ""
            echo "Mettez à jour votre .env avec:"
            echo "PUBLIC_BASE_URL=$url"
            echo ""
            echo "Note: cloudflared continue de tourner en arrière-plan"
            echo "Vous pouvez l'arrêter avec: pkill cloudflared"
            echo ""
        fi
    fi
done

