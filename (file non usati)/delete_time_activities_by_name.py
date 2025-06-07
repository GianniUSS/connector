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

def find_customer_by_name_fuzzy(customer_name):
    """Trova cliente con ricerca fuzzy se la ricerca esatta fallisce"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    
    # Prima prova ricerca esatta
    escaped_name = escape_sql_string(customer_name)
    query = f"SELECT * FROM Customer WHERE Name = '{escaped_name}' OR DisplayName = '{escaped_name}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.ok:
        customers = response.json().get("QueryResponse", {}).get("Customer", [])
        if customers:
            return customers
    
    # Se fallisce, prova ricerca con LIKE (più permissiva)
    logging.info("Ricerca esatta fallita, provo ricerca fuzzy...")
    
    # Rimuovi caratteri problematici per la ricerca fuzzy
    clean_name = customer_name.replace("'", "").replace('"', "").replace("(", "").replace(")", "")
    
    # Prova con diversi pattern
    search_patterns = [
        f"SELECT * FROM Customer WHERE Name LIKE '%{clean_name}%'",
        f"SELECT * FROM Customer WHERE DisplayName LIKE '%{clean_name}%'",
    ]
    
    for pattern in search_patterns:
        try:
            params = {"query": pattern}
            response = requests.get(url, headers=headers, params=params)
            
            if response.ok:
                customers = response.json().get("QueryResponse", {}).get("Customer", [])
                if customers:
                    logging.info(f"Trovati {len(customers)} clienti con ricerca fuzzy")
                    return customers
        except Exception as e:
            logging.warning(f"Errore in ricerca fuzzy: {e}")
            continue
    
    return []

def find_customer_by_displayname(display_name):
    """Trova un customer usando solo DisplayName - versione semplificata"""
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
                    logging.info(f"Customer trovato - ID: {customer['Id']}, DisplayName: {customer.get('DisplayName')}")
                    return customer
                else:
                    logging.error(f"Trovati {len(customers)} customer con lo stesso DisplayName: {display_name}")
                    for i, customer in enumerate(customers):
                        logging.error(f"  {i+1}. ID: {customer['Id']}, DisplayName: {customer.get('DisplayName')}")
                    return customers  # Ritorna tutti per scelta manuale
            else:
                logging.error(f"Nessun customer trovato con DisplayName: {display_name}")
                return None
        else:
            logging.error(f"Errore nella ricerca customer: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"Eccezione durante la ricerca customer: {str(e)}")
        return None

def find_subcustomers_by_parent_name(parent_name):
    """Trova tutti i sub-customer di un cliente principale"""
    # Prima trova il cliente principale
    parent = find_customer_by_name(parent_name)
    if not parent or isinstance(parent, list):
        return None
    
    parent_id = parent['Id']
    
    # Trova tutti i sub-customer
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM Customer WHERE ParentRef = '{parent_id}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        logging.error(f"Errore nella ricerca sub-customer: {response.status_code} - {response.text}")
        return None
    
    subcustomers = response.json().get("QueryResponse", {}).get("Customer", [])
    
    if subcustomers:
        logging.info(f"Trovati {len(subcustomers)} sub-customer per {parent_name}:")
        for sub in subcustomers:
            logging.info(f"  - ID: {sub['Id']}, Nome: {sub.get('DisplayName', sub.get('Name'))}")
    else:
        logging.info(f"Nessun sub-customer trovato per {parent_name}")
    
    return subcustomers

def delete_time_activities_by_customer(customer_id):
    """Elimina tutte le Time Activity di un cliente (funzione originale)"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM TimeActivity WHERE CustomerRef = '{customer_id}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        logging.error(f"Errore nella ricerca TimeActivity: {response.status_code} - {response.text}")
        return False
    
    activities = response.json().get("QueryResponse", {}).get("TimeActivity", [])
    if not activities:
        logging.info(f"Nessuna TimeActivity trovata per il cliente ID: {customer_id}")
        return True
    
    logging.info(f"Trovate {len(activities)} TimeActivity da eliminare")
    
    headers["Content-Type"] = "application/json"
    deleted_count = 0
    error_count = 0
    
    for activity in activities:
        activity_id = activity["Id"]
        sync_token = activity["SyncToken"]
        delete_url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/timeactivity?operation=delete"
        
        payload = {
            "Id": activity_id,
            "SyncToken": sync_token
        }
        
        del_resp = requests.post(delete_url, headers=headers, json=payload)
        if del_resp.ok:
            logging.info(f"Cancellata TimeActivity ID: {activity_id}")
            deleted_count += 1
        else:
            logging.error(f"Errore cancellazione ID {activity_id}: {del_resp.status_code} - {del_resp.text}")
            error_count += 1
    
    logging.info(f"Riepilogo: {deleted_count} eliminate, {error_count} errori")
    return error_count == 0

def delete_time_activities_by_subcustomer_name(subcustomer_name):
    """Elimina Time Activity partendo dal DisplayName del sub-customer"""
    
    # Trova il sub-customer direttamente per DisplayName
    customer = find_customer_by_displayname(subcustomer_name)
    
    if not customer:
        return False
    
    # Se trovati più clienti, chiedi quale scegliere
    if isinstance(customer, list):
        print("Trovati più clienti/sub-customer. Scegli quale:")
        for i, c in enumerate(customer):
            parent_info = ""
            if c.get('ParentRef'):
                parent_info = f" (Sub-customer di ID: {c['ParentRef']['value']})"
            print(f"  {i+1}. {c.get('DisplayName', c.get('Name'))} (ID: {c['Id']}){parent_info}")
        
        try:
            choice = int(input("Inserisci il numero: ")) - 1
            if 0 <= choice < len(customer):
                customer = customer[choice]
            else:
                logging.error("Scelta non valida")
                return False
        except ValueError:
            logging.error("Input non valido")
            return False
    
    customer_id = customer['Id']
    customer_display_name = customer.get('DisplayName', customer.get('Name'))
    
    # Verifica se è un sub-customer
    if customer.get('ParentRef'):
        parent_id = customer['ParentRef']['value']
        logging.info(f"Trovato sub-customer: {customer_display_name} (ID: {customer_id}, Parent: {parent_id})")
    else:
        logging.info(f"Attenzione: {customer_display_name} è un cliente principale, non un sub-customer")
    
    # Elimina Time Activity del sub-customer
    logging.info(f"Eliminando Time Activity per: {customer_display_name}")
    success = delete_time_activities_by_customer(customer_id)
    
    return success

def delete_time_activities_by_customer_name(customer_name, include_subcustomers=False):
    """Elimina Time Activity partendo dal DisplayName del cliente"""
    
    # Trova il cliente per DisplayName
    customer = find_customer_by_displayname(customer_name)
    
    if not customer:
        return False
    
    # Se trovati più clienti, chiedi quale scegliere
    if isinstance(customer, list):
        print("Trovati più clienti. Scegli quale:")
        for i, c in enumerate(customer):
            print(f"  {i+1}. {c.get('DisplayName', c.get('Name'))} (ID: {c['Id']})")
        
        try:
            choice = int(input("Inserisci il numero: ")) - 1
            if 0 <= choice < len(customer):
                customer = customer[choice]
            else:
                logging.error("Scelta non valida")
                return False
        except ValueError:
            logging.error("Input non valido")
            return False
    
    customer_id = customer['Id']
    customer_display_name = customer.get('DisplayName', customer.get('Name'))
    
    # Elimina Time Activity del cliente principale
    logging.info(f"Eliminando Time Activity per: {customer_display_name}")
    success = delete_time_activities_by_customer(customer_id)
    
    # Se richiesto, elimina anche per i sub-customer
    if include_subcustomers:
        subcustomers = find_subcustomers_by_parent_name(customer_display_name)
        if subcustomers:
            for subcustomer in subcustomers:
                sub_id = subcustomer['Id']
                sub_name = subcustomer.get('DisplayName', subcustomer.get('Name'))
                logging.info(f"Eliminando Time Activity per sub-customer: {sub_name}")
                sub_success = delete_time_activities_by_customer(sub_id)
                success = success and sub_success
    
    return success

def interactive_mode():
    """Modalità interattiva per scegliere le opzioni"""
    print("=== Eliminazione Time Activities ===")
    print("1. Elimina per nome sub-customer")
    print("2. Elimina per nome cliente principale (+ opzione sub-customer)")
    
    choice = input("Scegli opzione (1/2): ").strip()
    
    if choice == "1":
        # Modalità sub-customer
        subcustomer_name = input("Inserisci il nome del sub-customer: ").strip()
        if not subcustomer_name:
            print("Nome sub-customer richiesto!")
            return
        
        confirm = input(f"Confermi l'eliminazione per il sub-customer '{subcustomer_name}'? (s/n): ")
        if confirm.strip().lower() not in ['s', 'si', 'sì', 'y', 'yes']:
            print("Operazione annullata")
            return
        
        success = delete_time_activities_by_subcustomer_name(subcustomer_name)
        
    elif choice == "2":
        # Modalità cliente principale
        customer_name = input("Inserisci il nome del cliente: ").strip()
        if not customer_name:
            print("Nome cliente richiesto!")
            return
        
        include_subs = input("Includere anche i sub-customer? (s/n): ").strip().lower()
        include_subcustomers = include_subs in ['s', 'si', 'sì', 'y', 'yes']
        
        confirm = input(f"Confermi l'eliminazione per '{customer_name}'{' e sub-customer' if include_subcustomers else ''}? (s/n): ")
        if confirm.strip().lower() not in ['s', 'si', 'sì', 'y', 'yes']:
            print("Operazione annullata")
            return
        
        success = delete_time_activities_by_customer_name(customer_name, include_subcustomers)
    else:
        print("Scelta non valida!")
        return
    
    if success:
        print("✅ Operazione completata con successo!")
    else:
        print("❌ Operazione completata con errori. Controlla i log.")

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) == 1:
        # Modalità interattiva se nessun argomento
        interactive_mode()
    elif len(sys.argv) == 2:
        # DisplayName sub-customer (default) o cliente
        display_name = sys.argv[1]
        print("Cerco prima come sub-customer...")
        success = delete_time_activities_by_subcustomer_name(display_name)
        if not success:
            print("Non trovato come sub-customer, provo come cliente principale...")
            delete_time_activities_by_customer_name(display_name)
    elif len(sys.argv) == 3:
        # Opzioni specifiche
        display_name = sys.argv[1]
        option = sys.argv[2].lower()
        
        if option in ['sub', 'subcustomer', 's']:
            delete_time_activities_by_subcustomer_name(display_name)
        elif option in ['customer', 'cliente', 'c']:
            delete_time_activities_by_customer_name(display_name)
        elif option in ['all', 'tutti', 'a']:
            delete_time_activities_by_customer_name(display_name, include_subcustomers=True)
        else:
            print("Opzioni valide: sub, customer, all")
    else:
        print("Usage:")
        print("  python delete_time_activities.py                          # Modalità interattiva")
        print("  python delete_time_activities.py '<display_name>'         # Cerca come sub-customer, poi cliente")
        print("  python delete_time_activities.py '<display_name>' sub     # Solo sub-customer")
        print("  python delete_time_activities.py '<display_name>' customer # Solo cliente principale")
        print("  python delete_time_activities.py '<display_name>' all     # Cliente + tutti sub-customer")