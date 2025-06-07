import requests
import config
from token_manager import token_manager

def get_quickbooks_taxcodes():
    token_manager.load_refresh_token()  # Carica sempre il refresh token aggiornato
    access_token = token_manager.get_access_token()
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    # Query per TUTTI i TaxCode
    query = "SELECT * FROM TaxCode"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        taxcodes = data.get("QueryResponse", {}).get("TaxCode", [])
        # FILTRO: mostra solo quelli con 'Acquisti' nella descrizione
        taxcodes_acquisti = [t for t in taxcodes if t.get('Description') and 'Acquisti' in t.get('Description')]
        # Tutti i print disattivati
        return taxcodes_acquisti
    else:
        # print(f"Errore: {response.status_code} - {response.text}")
        return None

def get_quickbooks_taxcode_id_by_percent(percent):
    """
    Cerca il TaxCodeId QuickBooks dato un valore percentuale (es. 22) come stringa o int.
    Restituisce l'ID del TaxCode corrispondente a " IVA Acquisti al XX%" oppure None se non trovato.
    Filtra solo i TaxCode con 'Acquisti' nella descrizione.
    """
    token_manager.load_refresh_token()
    access_token = token_manager.get_access_token()
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    descr = f"IVA Acquisti al {int(percent)}%"
    query = f"SELECT * FROM TaxCode WHERE Description LIKE '%Acquisti%' AND Description LIKE '{descr}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        taxcodes = data.get("QueryResponse", {}).get("TaxCode", [])
        if taxcodes:
            taxcode_id = taxcodes[0].get("Id")
            return taxcode_id
        else:
            return None
    else:
        # print(f"Errore: {response.status_code} - {response.text}")
        return None

def get_quickbooks_taxcodes_acquisti():
    token_manager.load_refresh_token()  # Carica sempre il refresh token aggiornato
    access_token = token_manager.get_access_token()
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    # Query solo per i TaxCode di tipo Acquisti
    query = "SELECT * FROM TaxCode WHERE Description LIKE '%Acquisti%'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        taxcodes = data.get("QueryResponse", {}).get("TaxCode", [])
        # Tutti i print disattivati
        return taxcodes
    else:
        # print(f"Errore: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    # Mostra solo i TaxCode di acquisto (con filtro "Acquisti"), senza print
    get_quickbooks_taxcodes_acquisti()
