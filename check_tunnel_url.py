#!/usr/bin/env python3
"""Vérifier si le tunnel Cloudflare correspond au PUBLIC_BASE_URL."""

import sys
import subprocess
import requests
import re
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL


def check_cloudflared_process():
    """Vérifier si cloudflared est en cours d'exécution."""
    try:
        # Sur Windows (WSL), utiliser ps aux
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if 'cloudflared' in result.stdout.lower():
            lines = result.stdout.split('\n')
            cloudflared_lines = [line for line in lines if 'cloudflared' in line.lower() and 'grep' not in line.lower()]
            
            if cloudflared_lines:
                print("✅ cloudflared est en cours d'exécution")
                print("\nProcessus cloudflared trouvé(s):")
                for line in cloudflared_lines[:3]:  # Afficher max 3 lignes
                    # Nettoyer la ligne pour l'affichage
                    cleaned = ' '.join(line.split())
                    print(f"   {cleaned[:100]}...")
                return True
            else:
                print("❌ cloudflared n'est pas en cours d'exécution")
                return False
        else:
            print("❌ cloudflared n'est pas en cours d'exécution")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  Timeout lors de la vérification des processus")
        return None
    except FileNotFoundError:
        print("⚠️  Commande 'ps' non trouvée (peut-être Windows natif)")
        # Essayer avec tasklist sur Windows
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq cloudflared.exe'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if 'cloudflared.exe' in result.stdout:
                print("✅ cloudflared est en cours d'exécution (Windows)")
                return True
            else:
                print("❌ cloudflared n'est pas en cours d'exécution")
                return False
        except:
            print("⚠️  Impossible de vérifier les processus")
            return None
    except Exception as e:
        print(f"⚠️  Erreur lors de la vérification: {e}")
        return None


def get_tunnel_url_from_health():
    """Essayer de détecter l'URL du tunnel en testant PUBLIC_BASE_URL."""
    if not PUBLIC_BASE_URL:
        return None
    
    base_url = PUBLIC_BASE_URL.rstrip("/")
    
    # Tester l'endpoint /health
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        resp = requests.get(f"{base_url}/health", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            return base_url
        else:
            return None
    except requests.exceptions.RequestException:
        return None


def test_tunnel_connectivity():
    """Tester la connectivité du tunnel."""
    if not PUBLIC_BASE_URL:
        return False, "PUBLIC_BASE_URL non défini"
    
    base_url = PUBLIC_BASE_URL.rstrip("/")
    
    print(f"\n🔍 Test de connectivité pour: {base_url}")
    print("-" * 60)
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        # Test 1: Health endpoint
        print("   Test 1: /health endpoint...")
        resp = requests.get(f"{base_url}/health", headers=headers, timeout=10)
        
        if resp.status_code == 200:
            print(f"   ✅ /health accessible (Status: {resp.status_code})")
            health_ok = True
        else:
            print(f"   ❌ /health non accessible (Status: {resp.status_code})")
            health_ok = False
        
        # Test 2: Stickers route (même si 404, ça montre que la route existe)
        print("   Test 2: /stickers/ route...")
        resp2 = requests.get(f"{base_url}/stickers/test.webp", headers=headers, timeout=10)
        
        if resp2.status_code in [200, 404]:
            print(f"   ✅ Route /stickers/ accessible (Status: {resp2.status_code})")
            stickers_ok = True
        else:
            print(f"   ❌ Route /stickers/ non accessible (Status: {resp2.status_code})")
            stickers_ok = False
        
        # Test 3: GIFs route
        print("   Test 3: /gifs/ route...")
        resp3 = requests.get(f"{base_url}/gifs/test.mp4", headers=headers, timeout=10)
        
        if resp3.status_code in [200, 404]:
            print(f"   ✅ Route /gifs/ accessible (Status: {resp3.status_code})")
            gifs_ok = True
        else:
            print(f"   ❌ Route /gifs/ non accessible (Status: {resp3.status_code})")
            gifs_ok = False
        
        return health_ok and stickers_ok and gifs_ok, "Tous les tests réussis"
        
    except requests.exceptions.Timeout:
        return False, "Timeout - le tunnel ne répond pas"
    except requests.exceptions.ConnectionError as e:
        return False, f"Erreur de connexion: {str(e)[:100]}"
    except Exception as e:
        return False, f"Erreur: {str(e)[:100]}"


def extract_url_from_output(text):
    """Essayer d'extraire une URL du texte (pour les logs cloudflared)."""
    # Pattern pour les URLs Cloudflare Tunnel
    pattern = r'https://[a-z0-9-]+\.trycloudflare\.com'
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        return matches[0]
    return None


def main():
    """Vérifier si le tunnel correspond au PUBLIC_BASE_URL."""
    print("=" * 60)
    print("VÉRIFICATION TUNNEL CLOUDFLARE")
    print("=" * 60)
    
    # 1. Vérifier PUBLIC_BASE_URL
    print("\n📋 PUBLIC_BASE_URL:")
    if not PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL n'est pas défini dans .env")
        print("\n   Solution:")
        print("   Ajoutez dans votre .env:")
        print("   PUBLIC_BASE_URL=https://votre-url.trycloudflare.com")
        return 1
    else:
        base_url = PUBLIC_BASE_URL.rstrip("/")
        print(f"   ✅ PUBLIC_BASE_URL: {base_url}")
        
        # Vérifier si contient /whatsapp-webhook (erreur commune)
        if "/whatsapp-webhook" in base_url:
            print("\n   ⚠️  ATTENTION: PUBLIC_BASE_URL contient '/whatsapp-webhook'")
            print("   C'est incorrect! Il devrait être juste l'URL de base.")
            corrected = base_url.replace("/whatsapp-webhook", "")
            print(f"   URL correcte devrait être: {corrected}")
            print("\n   Mettez à jour votre .env:")
            print(f"   PUBLIC_BASE_URL={corrected}")
    
    # 2. Vérifier si cloudflared est en cours d'exécution
    print("\n" + "=" * 60)
    print("VÉRIFICATION PROCESSUS CLOUDFLARED")
    print("=" * 60)
    cloudflared_running = check_cloudflared_process()
    
    # 3. Tester la connectivité
    print("\n" + "=" * 60)
    print("TEST DE CONNECTIVITÉ")
    print("=" * 60)
    connectivity_ok, message = test_tunnel_connectivity()
    
    # 4. Résumé et recommandations
    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    
    if cloudflared_running is None:
        print("\n⚠️  Impossible de vérifier si cloudflared est en cours d'exécution")
    elif cloudflared_running:
        print("\n✅ cloudflared est en cours d'exécution")
    else:
        print("\n❌ cloudflared n'est PAS en cours d'exécution")
    
    if connectivity_ok:
        print("✅ Le tunnel est accessible et fonctionne correctement!")
        print(f"   URL: {base_url}")
    else:
        print(f"❌ Le tunnel n'est pas accessible: {message}")
    
    print("\n" + "=" * 60)
    print("RECOMMANDATIONS")
    print("=" * 60)
    
    if not cloudflared_running:
        print("\n1. Démarrer cloudflared:")
        print("   cloudflared tunnel --url http://localhost:5000")
        print("\n   Note: L'URL affichée par cloudflared doit correspondre à PUBLIC_BASE_URL")
    
    if not connectivity_ok:
        print("\n2. Vérifier:")
        print("   - Le serveur Flask est en cours d'exécution (port 5000)")
        print("   - cloudflared est démarré et affiche une URL")
        print("   - L'URL de cloudflared correspond à PUBLIC_BASE_URL")
        print("   - Aucun firewall ne bloque les connexions")
    
    if cloudflared_running and not connectivity_ok:
        print("\n3. Si cloudflared tourne mais n'est pas accessible:")
        print("   - Vérifier l'URL affichée par cloudflared")
        print("   - Mettre à jour PUBLIC_BASE_URL dans .env si nécessaire")
        print("   - Redémarrer le serveur Flask après modification")
    
    # 5. Instructions pour vérifier manuellement
    print("\n" + "=" * 60)
    print("VÉRIFICATION MANUELLE")
    print("=" * 60)
    print("\nPour vérifier que l'URL du tunnel correspond à PUBLIC_BASE_URL:")
    print("\n1. Regardez le terminal où cloudflared est en cours d'exécution")
    print("2. Cherchez une ligne qui ressemble à:")
    print("   +--------------------------------------------------------------------------------------------+")
    print("   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |")
    print("   |  https://xxxxx.trycloudflare.com                                                             |")
    print("   +--------------------------------------------------------------------------------------------+")
    print("\n3. Comparez cette URL avec PUBLIC_BASE_URL:")
    print(f"   PUBLIC_BASE_URL actuel: {base_url}")
    print("\n4. Si les URLs sont différentes:")
    print("   - Mettez à jour PUBLIC_BASE_URL dans votre .env")
    print("   - Redémarrez le serveur Flask")
    
    if cloudflared_running and connectivity_ok:
        print("\n✅ Tout est correctement configuré!")
        print("   Le tunnel Cloudflare correspond à PUBLIC_BASE_URL")
        return 0
    elif cloudflared_running and not connectivity_ok:
        print("\n⚠️  cloudflared est en cours d'exécution mais le tunnel n'est pas accessible")
        print("   Cela peut signifier:")
        print("   - L'URL du tunnel a changé (les URLs Cloudflare changent parfois)")
        print("   - Le tunnel n'est pas encore complètement initialisé")
        print("   - Il y a un problème réseau")
        print("\n   Action: Vérifiez l'URL affichée par cloudflared et mettez à jour PUBLIC_BASE_URL si nécessaire")
        return 1
    else:
        return 1


if __name__ == "__main__":
    exit(main())

