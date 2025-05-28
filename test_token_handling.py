"""
Test del meccanismo di gestione dei token QuickBooks.
Questo script permette di verificare che l'applicazione funzioni anche con token scaduti.
"""

import logging
from token_manager import TokenManager
import qb_customer
import sys

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def test_token_refresh():
    """Testa il refresh del token e verifica la gestione degli errori"""
    print("=== TEST REFRESH TOKEN ===")
    tm = TokenManager()
    tm.load_refresh_token()
    access_token = tm.get_access_token()
    
    print(f"Token ottenuto: {access_token[:10]}... (troncato)")
    
    if access_token == "invalid_token_handled_gracefully":
        print("✅ Il token non è valido ma è stato gestito correttamente")
    else:
        print(f"Token valido ottenuto: {access_token[:10]}...")

def test_customer_creation():
    """Testa la creazione di un cliente con token potenzialmente non valido"""
    print("\n=== TEST CREAZIONE CLIENTE ===")
    # Dati fittizi per un cliente di test
    test_customer = {
        "DisplayName": "Cliente Test Token",
        "CompanyName": "Azienda Test",
        "PrimaryEmailAddr": {"Address": "test@example.com"},
        "PrimaryPhone": {"FreeFormNumber": "1234567890"}
    }
    
    try:
        result = qb_customer.trova_o_crea_customer(test_customer["DisplayName"], test_customer)
        if result:
            print(f"✅ Cliente creato/trovato con successo: {result.get('DisplayName')}")
            print(f"   ID: {result.get('Id')}")
        else:
            print("❌ Errore nella creazione/ricerca del cliente")
    except Exception as e:
        print(f"❌ Eccezione: {e}")

def test_subcustomer_creation():
    """Testa la creazione di un sub-cliente con token potenzialmente non valido"""
    print("\n=== TEST CREAZIONE SUB-CLIENTE ===")
    # Prima otteniamo un cliente padre reale
    parent_customer = {
        "DisplayName": "Cliente Padre Test",
        "CompanyName": "Azienda Padre Test",
        "PrimaryEmailAddr": {"Address": "parent@example.com"},
        "PrimaryPhone": {"FreeFormNumber": "9876543210"}
    }
    
    # Creiamo o otteniamo il cliente padre
    parent_result = qb_customer.trova_o_crea_customer(parent_customer["DisplayName"], parent_customer)
    parent_id = parent_result.get("Id", "123456")  # Usiamo l'ID reale o un fallback
    
    # Dati fittizi per un sub-cliente di test
    test_subcustomer = {
        "DisplayName": "Sub-Cliente Test Token",
        "CompanyName": "Progetto Test",
        "PrimaryEmailAddr": {"Address": "test@example.com"},
        "PrimaryPhone": {"FreeFormNumber": "1234567890"}
    }
    
    try:
        result = qb_customer.trova_o_crea_subcustomer(test_subcustomer["DisplayName"], parent_id, test_subcustomer)
        if result:
            print(f"✅ Sub-cliente creato/trovato con successo: {result.get('DisplayName')}")
            print(f"   ID: {result.get('Id')}")
            print(f"   Parent ID: {result.get('ParentRef', {}).get('value')}")
        else:
            print("❌ Errore nella creazione/ricerca del sub-cliente")
    except Exception as e:
        print(f"❌ Eccezione: {e}")

if __name__ == "__main__":
    print("🧪 Inizio test gestione token...")
    
    test_token_refresh()
    test_customer_creation()
    test_subcustomer_creation()
    
    print("\n🏁 Test completati!")
