#!/usr/bin/env python3
"""Récupérer l'URL du tunnel Cloudflare depuis différentes sources."""

import subprocess
import re
import sys
import os
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL


def method1_check_cloudflared_metrics():
    """Méthode 1: Vérifier les métriques locales de cloudflared."""
    try:
        # cloudflared expose parfois des métriques sur localhost:4040
        import requests
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("tunnels"):
                tunnel = data["tunnels"][0]
                public_url = tunnel.get("public_url")
                if public_url:
                    return public_url
    except:
        pass
    return None


def method2_check_process_output():
    """Méthode 2: Vérifier la sortie du processus cloudflared."""
    try:
        # Essayer de lire depuis /proc si disponible (Linux)
        pid = None
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        for line in result.stdout.split('\n'):
            if 'cloudflared' in line.lower() and 'grep' not in line.lower():
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        break
                    except:
                        pass
        
        if pid:
            # Essayer de lire depuis /proc/PID/fd/1 (stdout)
            try:
                stdout_path = Path(f"/proc/{pid}/fd/1")
                if stdout_path.exists():
                    # Note: On ne peut pas vraiment lire depuis /proc/fd directement
                    # Mais on peut essayer de capturer via d'autres moyens
                    pass
            except:
                pass
    except:
        pass
    return None


def method3_restart_and_capture():
    """Méthode 3: Redémarrer cloudflared et capturer l'URL."""
    print("\n⚠️  Cette méthode nécessite de redémarrer cloudflared.")
    print("   Voulez-vous continuer? (y/n): ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        return None
    
    print("\n🔄 Arrêt de cloudflared...")
    try:
        subprocess.run(['pkill', 'cloudflared'], timeout=5)
        time.sleep(1)
    except:
        pass
    
    print("🚀 Démarrage de cloudflared avec capture de sortie...")
    try:
        process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Attendre un peu pour que cloudflared démarre
        time.sleep(3)
        
        # Lire les premières lignes de sortie
        url_pattern = r'https://[a-z0-9-]+\.trycloudflare\.com'
        max_wait = 10
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            line = process.stdout.readline()
            if not line:
                time.sleep(0.5)
                continue
            
            print(f"   {line.strip()}")
            matches = re.findall(url_pattern, line, re.IGNORECASE)
            if matches:
                url = matches[0]
                print(f"\n✅ URL trouvée: {url}")
                print("\n⚠️  Note: cloudflared continue de tourner en arrière-plan")
                print("   Vous pouvez le laisser tourner ou l'arrêter avec: pkill cloudflared")
                return url
        
        print("\n⚠️  Timeout - URL non trouvée dans la sortie")
        return None
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def method4_test_common_urls():
    """Méthode 4: Tester des URLs communes ou suggérées."""
    print("\n🔍 Test de connectivité avec PUBLIC_BASE_URL...")
    
    if not PUBLIC_BASE_URL:
        return None
    
    base_url = PUBLIC_BASE_URL.rstrip("/")
    
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        resp = requests.get(f"{base_url}/health", headers=headers, timeout=5)
        
        if resp.status_code == 200:
            print(f"✅ {base_url} est accessible!")
            return base_url
        else:
            print(f"❌ {base_url} retourne {resp.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ {base_url} n'est pas accessible: {str(e)[:100]}")
    
    return None


def method5_check_logs():
    """Méthode 5: Vérifier les logs système."""
    print("\n🔍 Recherche dans les logs système...")
    
    # Vérifier les logs récents
    log_commands = [
        ['journalctl', '-u', 'cloudflared', '-n', '50', '--no-pager'],
        ['dmesg', '|', 'grep', 'cloudflared'],
    ]
    
    url_pattern = r'https://[a-z0-9-]+\.trycloudflare\.com'
    
    for cmd in log_commands:
        try:
            result = subprocess.run(
                cmd[0] if isinstance(cmd, list) else cmd.split(),
                capture_output=True,
                text=True,
                timeout=5
            )
            matches = re.findall(url_pattern, result.stdout, re.IGNORECASE)
            if matches:
                return matches[0]
        except:
            pass
    
    return None


def main():
    """Récupérer l'URL du tunnel Cloudflare."""
    print("=" * 60)
    print("RÉCUPÉRATION URL TUNNEL CLOUDFLARE")
    print("=" * 60)
    
    methods = [
        ("Test de PUBLIC_BASE_URL", method4_test_common_urls),
        ("Métriques cloudflared (localhost:4040)", method1_check_cloudflared_metrics),
        ("Logs système", method5_check_logs),
    ]
    
    found_url = None
    
    for method_name, method_func in methods:
        print(f"\n{'=' * 60}")
        print(f"MÉTHODE: {method_name}")
        print("=" * 60)
        try:
            url = method_func()
            if url:
                found_url = url
                break
        except Exception as e:
            print(f"⚠️  Erreur: {e}")
            continue
    
    if not found_url:
        print("\n" + "=" * 60)
        print("AUCUNE URL TROUVÉE AUTOMATIQUEMENT")
        print("=" * 60)
        print("\n💡 Solutions manuelles:")
        print("\n1. Regardez le terminal où cloudflared a été démarré")
        print("   L'URL devrait être affichée au démarrage, par exemple:")
        print("   +--------------------------------------------------------------------------------------------+")
        print("   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |")
        print("   |  https://xxxxx.trycloudflare.com                                                             |")
        print("   +--------------------------------------------------------------------------------------------+")
        
        print("\n2. Redémarrer cloudflared et capturer l'URL:")
        print("   a) Arrêtez cloudflared: pkill cloudflared")
        print("   b) Redémarrez-le: cloudflared tunnel --url http://localhost:5000")
        print("   c) Copiez l'URL affichée")
        
        print("\n3. Utiliser la méthode interactive:")
        response = input("\n   Voulez-vous redémarrer cloudflared pour capturer l'URL? (y/n): ").strip().lower()
        if response == 'y':
            found_url = method3_restart_and_capture()
    
    if found_url:
        print("\n" + "=" * 60)
        print("URL TROUVÉE")
        print("=" * 60)
        print(f"\n✅ URL du tunnel: {found_url}")
        
        if PUBLIC_BASE_URL:
            current_url = PUBLIC_BASE_URL.rstrip("/")
            if found_url.lower() != current_url.lower():
                print(f"\n⚠️  PUBLIC_BASE_URL actuel: {current_url}")
                print("   Les URLs ne correspondent pas!")
                print(f"\n   Mettez à jour votre .env avec:")
                print(f"   PUBLIC_BASE_URL={found_url}")
            else:
                print(f"\n✅ PUBLIC_BASE_URL correspond à l'URL du tunnel!")
        else:
            print(f"\n   Ajoutez dans votre .env:")
            print(f"   PUBLIC_BASE_URL={found_url}")
        
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())

