#!/usr/bin/env python3
"""
Launcher per app Flask con debug e gestione errori
"""

import sys
import os

def start_flask_app():
    """Avvia l'app Flask con gestione errori completa"""
    
    print("🚀 Avvio AppConnector Flask con v2.0 ottimizzata...")
    
    try:
        # Verifica presenza file necessari
        required_files = ['app.py', 'config.py', 'rentman_api_fast_v2.py']
        for file in required_files:
            if not os.path.exists(file):
                print(f"❌ File mancante: {file}")
                return False
        
        print("✅ File necessari presenti")
        
        # Import dell'app
        print("🔄 Importazione moduli...")
        from app import app
        print("✅ App Flask importata correttamente")
        
        # Test rapido della funzione principale
        print("🔄 Test funzione list_projects_by_date...")
        from rentman_api_fast_v2 import list_projects_by_date
        print("✅ Funzione v2.0 importata correttamente")
        
        # Avvia l'app in modalità debug
        print("\n🌐 Avvio server Flask su http://127.0.0.1:5000")
        print("📱 Premi Ctrl+C per fermare il server")
        print("-" * 50)
        
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=False  # Evita problemi con il reloader
        )
        
    except ImportError as e:
        print(f"❌ Errore di importazione: {e}")
        print("🔍 Controlla che tutti i moduli necessari siano presenti")
        return False
        
    except SyntaxError as e:
        print(f"❌ Errore di sintassi: {e}")
        print(f"📍 File: {e.filename}, Linea: {e.lineno}")
        return False
        
    except Exception as e:
        print(f"❌ Errore generico: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_flask_app()
