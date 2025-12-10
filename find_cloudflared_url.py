#!/usr/bin/env python3
"""Trouver l'URL de cloudflared sans le redémarrer."""

import subprocess
import re
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def find_url_in_history():
    """Chercher l'URL dans l'historique du shell."""
    print("🔍 Recherche dans l'historique du shell...")
    
    history_files = [
        Path.home() / ".bash_history",
        Path.home() / ".zsh_history",
        Path.home() / ".history",
    ]
    
    url_pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com', re.IGNORECASE)
    urls_found = set()
    
    for hist_file in history_files:
        if hist_file.exists():
            try:
                with open(hist_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = url_pattern.findall(content)
                    urls_found.update(matches)
            except:
                pass
    
    return list(urls_found)


def test_urls(urls):
    """Tester une liste d'URLs pour voir laquelle fonctionne."""
    import requests
    
    print("\n🧪 Test de connectivité des URLs trouvées...")
    
    for url in urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            resp = requests.get(f"{url}/health", headers=headers, timeout=5)
            if resp.status_code == 200:
                return url
        except:
            continue
    
    return None


def main():
    """Trouver l'URL de cloudflared."""
    print("=" * 60)
    print("RECHERCHE URL CLOUDFLARE TUNNEL")
    print("=" * 60)
    print("\nMéthode non-intrusive: recherche dans l'historique...")
    
    urls = find_url_in_history()
    
    if urls:
        print(f"\n✅ {len(urls)} URL(s) trouvée(s) dans l'historique:")
        for url in urls:
            print(f"   - {url}")
        
        # Tester les URLs
        working_url = test_urls(urls)
        
        if working_url:
            print(f"\n✅ URL fonctionnelle trouvée: {working_url}")
            print("\nMettez à jour votre .env avec:")
            print(f"PUBLIC_BASE_URL={working_url}")
            return 0
        else:
            print("\n⚠️  Aucune des URLs trouvées n'est accessible")
            print("   Elles peuvent être expirées")
    
    print("\n" + "=" * 60)
    print("INSTRUCTIONS MANUELLES")
    print("=" * 60)
    print("\nPour trouver l'URL de cloudflared:")
    print("\n1. Regardez le terminal où cloudflared a été démarré")
    print("   L'URL devrait être affichée, par exemple:")
    print("   +--------------------------------------------------------------------------------------------+")
    print("   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |")
    print("   |  https://xxxxx.trycloudflare.com                                                             |")
    print("   +--------------------------------------------------------------------------------------------+")
    print("\n2. Si vous ne trouvez pas l'URL, redémarrez cloudflared:")
    print("   pkill cloudflared")
    print("   cloudflared tunnel --url http://localhost:5000")
    print("   (L'URL sera affichée au démarrage)")
    print("\n3. Ou utilisez le script interactif:")
    print("   python capture_cloudflared_url.py")
    
    return 1


if __name__ == "__main__":
    exit(main())

