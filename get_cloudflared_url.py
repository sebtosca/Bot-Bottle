#!/usr/bin/env python3
"""Obtenir l'URL actuelle du tunnel Cloudflare depuis les processus ou logs."""

import subprocess
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL


def get_cloudflared_url_from_process():
    """Essayer d'obtenir l'URL depuis les arguments du processus cloudflared."""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.split('\n')
        for line in lines:
            if 'cloudflared' in line.lower() and 'grep' not in line.lower():
                # Chercher une URL dans la ligne
                url_pattern = r'https://[a-z0-9-]+\.trycloudflare\.com'
                matches = re.findall(url_pattern, line, re.IGNORECASE)
                if matches:
                    return matches[0]
        
        return None
    except Exception as e:
        print(f"⚠️  Erreur: {e}")
        return None


def check_url_match():
    """Vérifier si PUBLIC_BASE_URL correspond à l'URL du tunnel."""
    print("=" * 60)
    print("VÉRIFICATION URL TUNNEL CLOUDFLARE")
    print("=" * 60)
    
    if not PUBLIC_BASE_URL:
        print("\n❌ PUBLIC_BASE_URL n'est pas défini")
        return 1
    
    configured_url = PUBLIC_BASE_URL.rstrip("/")
    print(f"\n📋 PUBLIC_BASE_URL configuré: {configured_url}")
    
    # Essayer d'obtenir l'URL depuis le processus
    print("\n🔍 Recherche de l'URL dans les processus cloudflared...")
    process_url = get_cloudflared_url_from_process()
    
    if process_url:
        print(f"   URL trouvée dans le processus: {process_url}")
    else:
        print("   ⚠️  Impossible d'extraire l'URL depuis les processus")
        print("\n   💡 Pour vérifier manuellement:")
        print("   1. Regardez la sortie de cloudflared dans votre terminal")
        print("   2. Cherchez une ligne comme: 'https://xxxxx.trycloudflare.com'")
        print("   3. Comparez avec PUBLIC_BASE_URL")
    
    print("\n" + "=" * 60)
    print("COMPARAISON")
    print("=" * 60)
    
    if process_url:
        if process_url.lower() == configured_url.lower():
            print("✅ Les URLs correspondent!")
            print(f"   {configured_url}")
            return 0
        else:
            print("❌ Les URLs NE correspondent PAS!")
            print(f"   PUBLIC_BASE_URL: {configured_url}")
            print(f"   URL du tunnel:   {process_url}")
            print("\n   Solution:")
            print(f"   Mettez à jour votre .env avec:")
            print(f"   PUBLIC_BASE_URL={process_url}")
            return 1
    else:
        print("⚠️  Impossible de comparer automatiquement")
        print("\n   Vérifiez manuellement:")
        print("   1. Regardez la sortie de cloudflared")
        print("   2. Comparez l'URL affichée avec PUBLIC_BASE_URL")
        print(f"   3. PUBLIC_BASE_URL actuel: {configured_url}")
        return 2


if __name__ == "__main__":
    exit(check_url_match())

