#!/usr/bin/env python3
"""Capturer l'URL de cloudflared en le redémarrant."""

import subprocess
import re
import sys
import time
import signal
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import PUBLIC_BASE_URL


def capture_url():
    """Redémarrer cloudflared et capturer l'URL."""
    print("=" * 60)
    print("CAPTURE URL CLOUDFLARE TUNNEL")
    print("=" * 60)
    print("\nCe script va:")
    print("1. Arrêter cloudflared s'il est en cours d'exécution")
    print("2. Redémarrer cloudflared et capturer l'URL")
    print("\n⚠️  Note: cloudflared continuera de tourner après la capture")
    print()
    
    response = input("Continuer? (y/n): ").strip().lower()
    if response != 'y':
        print("Annulé.")
        return None
    
    # Arrêter cloudflared
    print("\n🛑 Arrêt de cloudflared...")
    try:
        subprocess.run(['pkill', 'cloudflared'], timeout=5, 
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except:
        pass
    
    # Démarrer cloudflared
    print("🚀 Démarrage de cloudflared...")
    print("\n" + "=" * 60)
    print("ATTENDEZ QUE L'URL APPARAISSE CI-DESSOUS")
    print("=" * 60)
    print()
    
    url_pattern = re.compile(r'https://[a-z0-9-]+\.trycloudflare\.com', re.IGNORECASE)
    found_url = None
    process = None
    
    try:
        process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', 'http://localhost:5000'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Lire la sortie ligne par ligne
        max_wait = 30  # Attendre max 30 secondes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if process.poll() is not None:
                # Processus terminé
                break
            
            line = process.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # Afficher la ligne
            print(line.rstrip())
            
            # Chercher l'URL
            matches = url_pattern.findall(line)
            if matches and not found_url:
                found_url = matches[0]
                print("\n" + "=" * 60)
                print(f"✅ URL TROUVÉE: {found_url}")
                print("=" * 60)
                print()
                print("Mettez à jour votre .env avec:")
                print(f"PUBLIC_BASE_URL={found_url}")
                print()
                
                if PUBLIC_BASE_URL:
                    current_url = PUBLIC_BASE_URL.rstrip("/")
                    if found_url.lower() != current_url.lower():
                        print(f"⚠️  PUBLIC_BASE_URL actuel: {current_url}")
                        print("   Les URLs ne correspondent pas!")
                    else:
                        print("✅ PUBLIC_BASE_URL correspond déjà!")
                
                print("\nNote: cloudflared continue de tourner en arrière-plan")
                print("Vous pouvez l'arrêter avec: pkill cloudflared")
                print()
                break
        
        if not found_url:
            print("\n⚠️  URL non trouvée dans les 30 premières secondes")
            print("   Vérifiez manuellement la sortie ci-dessus")
            print("   ou regardez le terminal où cloudflared tourne")
        
        return found_url
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par l'utilisateur")
        if process:
            process.terminate()
        return None
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        if process:
            process.terminate()
        return None


def main():
    """Point d'entrée principal."""
    url = capture_url()
    
    if url:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())

