"""
Test di funzionamento con token scaduto.
Questo script verifica che l'applicazione gestisca correttamente la modalità simulazione.
"""

import logging
from token_manager import TokenManager
from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
from create_or_update_invoice_for_project import create_or_update_invoice_for_project
from main_invoice_only import main_invoice_only

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def test_token_simulazione():
    """Verifica che l'applicazione riconosca un token non valido"""
    print("=== TEST TOKEN SIMULAZIONE ===")
    tm = TokenManager()
    tm.load_refresh_token()
    token = tm.get_access_token()
    
    if token == "invalid_token_handled_gracefully":
        print("✅ Rilevato token non valido - Modalità simulazione attiva")
    else:
        print("⚠️ Token valido trovato - I test seguenti non saranno in modalità simulazione")
    
    return token == "invalid_token_handled_gracefully"

def test_invoice_simulazione():
    """Testa la creazione di una fattura in modalità simulazione"""
    print("\n=== TEST FATTURA SIMULAZIONE ===")
    
    # Dati di esempio per test
    result = create_or_update_invoice_for_project(
        subcustomer_id="789012",  # ID fittizio del subcustomer
        project_id="9999",
        project_number="TEST-SIM",
        amount=100.0,
        descrizione="Fattura di test simulazione",
        invoice_date="2025-05-27"
    )
    
    print(f"Risultato: {result}")
    
    if result.get("simulated", False):
        print("✅ Fattura generata in modalità simulazione")
    else:
        print("❌ Fattura non in modalità simulazione")
    
    return result

def test_main_invoice_only():
    """Testa il flusso completo di fatturazione tramite main_invoice_only"""
    print("\n=== TEST MAIN_INVOICE_ONLY SIMULAZIONE ===")
    
    try:
        # Usa un ID di progetto di test
        result = main_invoice_only("3660")  # Usa un ID esistente nei log
        
        print(f"Risultato: {result}")
        
        if result.get("simulated", False):
            print("✅ Processo fatturazione completato in modalità simulazione")
        else:
            print("❌ Processo fatturazione non in modalità simulazione")
            
        return result
    except Exception as e:
        print(f"❌ Errore durante test main_invoice_only: {e}")
        return None

if __name__ == "__main__":
    print("🧪 INIZIO TEST MODALITÀ SIMULAZIONE")
    
    is_simulation_mode = test_token_simulazione()
    
    if is_simulation_mode:
        print("\n⚠️ MODALITÀ SIMULAZIONE ATTIVA - Token QuickBooks non valido")
        
        invoice_result = test_invoice_simulazione()
        main_result = test_main_invoice_only()
        
        print("\n=== RIEPILOGO TEST ===")
        print("✅ Modalità simulazione correttamente attivata")
        print(f"  • Fattura simulata: ID={invoice_result.get('invoice_id', 'N/A')}")
        if main_result:
            print(f"  • Main invoice only: Progetto={main_result.get('project_id', 'N/A')}")
        
        print("\n⚙️ Per ripristinare il funzionamento completo:")
        print("1. Segui le istruzioni in AGGIORNAMENTO_TOKEN_QUICKBOOKS.md per ottenere un nuovo token")
        print("2. Aggiorna il file config.py con il nuovo token")
    else:
        print("\n✅ TOKEN VALIDO - Modalità normale attiva")
        print("Non è necessario aggiornare il token QuickBooks.")
    
    print("\n🏁 TEST COMPLETATI!")
