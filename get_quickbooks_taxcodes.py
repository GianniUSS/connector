import requests
import config
from token_manager import TokenManager

def get_quickbooks_taxcodes():
    tm = TokenManager()
    tm.load_refresh_token()  # Carica sempre il refresh token aggiornato
    access_token = tm.get_access_token()
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    # Query solo per TaxCode con descrizione esatta 'IVA Acquisti al 22%'
    query = "SELECT * FROM TaxCode WHERE Description LIKE 'IVA Acquisti al 22%'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    print(f"[get_quickbooks_taxcodes] Chiamata a: {url} (query: {query})")
    response = requests.get(url, headers=headers, params=params)
    print(f"[get_quickbooks_taxcodes] Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        taxcodes = data.get("QueryResponse", {}).get("TaxCode", [])
        print("Lista codici TaxCode trovati:")
        for t in taxcodes:
            print(f"- {t.get('Name')} (ID: {t.get('Id')})")
        return taxcodes
    else:
        print(f"Errore: {response.status_code} - {response.text}")
        return None

def get_quickbooks_taxcode_id_by_percent(percent):
    """
    Cerca il TaxCodeId QuickBooks dato un valore percentuale (es. 22) come stringa o int.
    Restituisce l'ID del TaxCode corrispondente a "IVA Acquisti al XX%" oppure None se non trovato.
    """
    tm = TokenManager()
    tm.load_refresh_token()
    access_token = tm.get_access_token()
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    descr = f"IVA Acquisti al {int(percent)}%"
    query = f"SELECT * FROM TaxCode WHERE Description LIKE '{descr}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    print(f"[get_quickbooks_taxcode_id_by_percent] Query: {query}")
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        taxcodes = data.get("QueryResponse", {}).get("TaxCode", [])
        if taxcodes:
            taxcode_id = taxcodes[0].get("Id")
            print(f"Trovato TaxCodeId: {taxcode_id} per {descr}")
            return taxcode_id
        else:
            print(f"Nessun TaxCode trovato per {descr}")
            return None
    else:
        print(f"Errore: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    get_quickbooks_taxcodes()
