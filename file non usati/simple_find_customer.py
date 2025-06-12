import requests
import config
from token_manager import token_manager
import logging

token_manager.load_refresh_token()
access_token = token_manager.get_access_token()

def escape_sql_string(value):
    """Escape dei caratteri speciali per le query SQL di QuickBooks"""
    if not value:
        return value
    # Escape degli apici singoli (raddoppiarli)
    escaped = value.replace("'", "''")
    return escaped

def find_customer_id_by_displayname(display_name):
    """
    Trova l'ID di un customer usando solo DisplayName
    Ritorna l'ID se trovato, None se non trovato
    """
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Escape del nome per la query SQL
    escaped_name = escape_sql_string(display_name)
    query = f"SELECT * FROM Customer WHERE DisplayName = '{escaped_name}'"
    
    try:
        response = requests.get(url, headers=headers, params={"query": query})
        
        if response.ok:
            data = response.json()
            customers = data.get("QueryResponse", {}).get("Customer", [])
            
            if customers:
                if len(customers) == 1:
                    customer = customers[0]
                    customer_id = customer['Id']
                    logging.info(f"Customer trovato - ID: {customer_id}, DisplayName: {customer.get('DisplayName')}")
                    return customer_id
                else:
                    logging.error(f"Trovati {len(customers)} customer con lo stesso DisplayName: {display_name}")
                    for i, customer in enumerate(customers):
                        logging.error(f"  {i+1}. ID: {customer['Id']}, DisplayName: {customer.get('DisplayName')}")
                    return None
            else:
                logging.error(f"Nessun customer trovato con DisplayName: {display_name}")
                return None
        else:
            logging.error(f"Errore nella ricerca customer: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Eccezione durante la ricerca customer: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) < 2:
        print("Usage: python simple_find_customer.py '<display_name>'")
        sys.exit(1)
    
    display_name = sys.argv[1]
    customer_id = find_customer_id_by_displayname(display_name)
    
    if customer_id:
        print(f"✅ Customer ID: {customer_id}")
    else:
        print("❌ Customer non trovato")
        sys.exit(1)