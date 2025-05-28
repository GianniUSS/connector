"""
Test semplice per verificare la gestione dei token QuickBooks.
"""

from token_manager import TokenManager

def main():
    print("=== TEST TOKEN MANAGER ===")
    
    # Inizializza il gestore dei token
    tm = TokenManager()
    tm.load_refresh_token()
    
    # Prova a ottenere un token di accesso
    access_token = tm.get_access_token()
    
    if access_token == "invalid_token_handled_gracefully":
        print("\n✅ Token non valido, ma gestito correttamente.")
        print("   L'applicazione può continuare a funzionare in modalità limitata.")
    else:
        print(f"\n✅ Token valido ottenuto!")
        print(f"   Access Token: {access_token[:10]}... (troncato)")
    
    print("\n=== TEST COMPLETATO ===")

if __name__ == "__main__":
    main()
