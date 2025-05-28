import requests
import config
from token_manager import TokenManager

def get_customers():
    token_manager = TokenManager()
    token_manager.load_refresh_token()
    access_token = token_manager.get_access_token()
    url = f"{config.API_BASE_URL}{config.REALM_ID}/query"
    query = "SELECT * FROM Customer"
    params = {"query": query}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Errore chiamata API:", response.status_code, response.text)
        return None

def find_customer_by_displayname(display_name):
    token_manager = TokenManager()
    token_manager.load_refresh_token()
    access_token = token_manager.get_access_token()
    url = f"{config.API_BASE_URL}{config.REALM_ID}/query"
    query = f"SELECT * FROM Customer WHERE DisplayName='{display_name}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        customers = data.get("QueryResponse", {}).get("Customer", [])
        if customers:
            return customers[0]  # ritorna il primo trovato
    else:
        print("Errore ricerca Customer:", response.status_code, response.text)
    return None
