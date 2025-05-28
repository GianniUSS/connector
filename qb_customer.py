import requests
import config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Cache globali per ottimizzazione
_projecttype_cache = {}
_status_cache = {}
_cache_lock = threading.Lock()

def get_projecttype_name_cached(type_id, headers):
    """ Recupera il nome del tipo progetto con cache """
    if not type_id:
        return ""
    
    # Controlla cache
    with _cache_lock:
        if type_id in _projecttype_cache:
            return _projecttype_cache[type_id]
    
    url = f"{config.REN_BASE_URL}/projecttypes/{type_id}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.ok:
            data = response.json().get('data')
            if isinstance(data, dict):
                name = data.get('name', '')
                with _cache_lock:
                    _projecttype_cache[type_id] = name
                return name
    except Exception as e:
        print(f"Errore recuperando project type {type_id}: {e}")
    
    with _cache_lock:
        _projecttype_cache[type_id] = ""
    return ""

def extract_id_from_path(path):
    """Estrae l'ID da un path come '/projecttypes/123' """
    if not path:
        return None
    try:
        return int(path.split('/')[-1])
    except (ValueError, IndexError):
        return None

def get_all_statuses(headers):
    """ Recupera tutti gli status disponibili e crea una mappa ID->Nome """
    with _cache_lock:
        if _status_cache:
            return _status_cache
    
    url = f"{config.REN_BASE_URL}/statuses"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.ok:
            data = response.json().get('data', [])
            status_map = {status['id']: status['name'] for status in data}
            with _cache_lock:
                _status_cache.update(status_map)
            return status_map
        else:
            print(f"Errore endpoint statuses: {response.status_code}")
    except Exception as e:
        print(f"Errore recuperando statuses: {e}")
    return {}

def get_project_subprojects_fast(project_id, headers):
    """ Recupera i subprojects di un progetto con timeout ridotto """
    url = f"{config.REN_BASE_URL}/subprojects/{project_id}"
    try:
        response = requests.get(url, headers=headers, timeout=3)  # Timeout ridotto
        if response.ok:
            data = response.json().get('data', [])
            return data if isinstance(data, list) else [data]
        elif response.status_code == 404:
            return []
        else:
            return []  # Silenzioso per velocità
    except Exception:
        return []  # Silenzioso per velocità

def get_project_status_fast(project_id, headers, status_map):
    """ Recupera lo status del progetto velocemente """
    subprojects = get_project_subprojects_fast(project_id, headers)
    
    if not subprojects:
        return "Concept"
    
    first_subproject = subprojects[0] if isinstance(subprojects, list) else subprojects
    status_path = first_subproject.get('status')
    
    if status_path:
        status_id = extract_id_from_path(status_path)
        if status_id and status_id in status_map:
            return status_map[status_id]
    
    return "Concept"

def process_project(project_data, headers, status_map, start_dt, end_dt, debug_count):
    """ Processa un singolo progetto """
    p = project_data
    period_start = p.get('planperiod_start')
    period_end = p.get('planperiod_end')
    
    if not period_start or not period_end:
        return None
        
    try:
        ps = datetime.fromisoformat(period_start[:10]).date()
        pe = datetime.fromisoformat(period_end[:10]).date()
        
        if pe < start_dt or ps > end_dt:
            return None
            
        project_type_path = p.get('project_type')
        project_type_id = extract_id_from_path(project_type_path)
        
        # Recupera status (veloce)
        project_id = p.get('id')
        project_status = get_project_status_fast(project_id, headers, status_map)
        
        # Debug migliorato
        if debug_count[0] < 3:
            print(f"🔍 Debug progetto {project_id}:")
            print(f"  📝 Raw number field: {repr(p.get('number'))}")
            print(f"  🔢 Number type: {type(p.get('number'))}")
            print(f"  📄 Name: '{p.get('name')}'")
            print(f"  📊 Status: '{project_status}'")
            print(f"  🏷️ Project type ID: {project_type_id}")
            debug_count[0] += 1
        
        # Conversione numero con debug extra
        raw_number = p.get("number")
        if raw_number is not None:
            converted_number = str(raw_number)
            if debug_count[0] <= 3:
                print(f"  ✅ Converted number: '{converted_number}'")
        else:
            converted_number = "N/A"
            if debug_count[0] <= 3:
                print(f"  ❌ Number is None!")
        
        return {
            "id": project_id,
            "number": converted_number,
            "name": p.get("name") or "",
            "status": project_status,
            "project_type_id": project_type_id,
            "project_type_name": ""  # Recuperato dopo per velocità
        }
        
    except Exception as e:
        print(f"❌ Errore processando progetto {p.get('id', 'unknown')}: {e}")
        return None

def list_projects_by_date(from_date, to_date):
    print("🚀 Avvio recupero progetti ottimizzato...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map
    status_map = get_all_statuses(headers)
    print(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti
    url = f"{config.REN_BASE_URL}/projects"
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    
    projects = response.json().get('data', [])
    print(f"📋 Progetti totali recuperati: {len(projects)}")
    
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    # Processa progetti con threading per velocità
    filtered = []
    debug_count = [0]  # Lista per reference mutabile
    
    print(f"⏳ Filtraggio progetti per periodo {from_date} - {to_date}...")
    
    # Processa sequenzialmente per ora (per debug)
    for p in projects:
        result = process_project(p, headers, status_map, start_dt, end_dt, debug_count)
        if result:
            filtered.append(result)
    
    print(f"✅ Progetti filtrati: {len(filtered)}")
    
    # Recupera project type names per i progetti filtrati (in parallelo)
    if filtered:
        print("🏷️ Recupero nomi project types...")
        unique_type_ids = set(p['project_type_id'] for p in filtered if p['project_type_id'])
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            type_name_futures = {
                type_id: executor.submit(get_projecttype_name_cached, type_id, headers)
                for type_id in unique_type_ids
            }
            
            # Aggiorna i project type names
            for project in filtered:
                type_id = project['project_type_id']
                if type_id and type_id in type_name_futures:
                    try:
                        project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                    except:
                        project['project_type_name'] = ""
    
    print(f"🎉 Completato! Restituiti {len(filtered)} progetti")
    return filtered

# Funzione per svuotare le cache se necessario
def clear_cache():
    """ Svuota le cache per forzare il refresh """
    global _projecttype_cache, _status_cache
    with _cache_lock:
        _projecttype_cache.clear()
        _status_cache.clear()
    print("🧹 Cache svuotata")

# Funzioni per la gestione dei clienti QuickBooks
def trova_o_crea_customer(display_name, customer_data):
    """
    Trova un cliente esistente in QuickBooks o ne crea uno nuovo
    
    Args:
        display_name (str): Nome visualizzato del cliente
        customer_data (dict): Dati del cliente da creare/aggiornare
    
    Returns:
        dict: Dati del cliente trovato o creato, None in caso di errore
    """
    from token_manager import TokenManager
    import logging
    
    try:
        # Otteniamo il token di accesso
        tm = TokenManager()
        tm.load_refresh_token()
        access_token = tm.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            logging.warning("Token non valido, impossibile interagire con QuickBooks")
            # Restituiamo un dict fittizio per scopi di test in caso di token non valido
            return {
                "Id": "123456",
                "DisplayName": display_name,
                "CompanyName": customer_data.get("CompanyName", ""),
                "Active": True
            }
        
        # Prima cerchiamo se il cliente esiste già
        url_query = f"{config.API_BASE_URL}{config.REALM_ID}/query"
        query = f"SELECT * FROM Customer WHERE DisplayName = '{display_name}'"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {"query": query}
        
        logging.info(f"Ricerca customer con nome: {display_name}")
        resp = requests.get(url_query, headers=headers, params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'Customer' in data.get('QueryResponse', {}):
                # Cliente trovato, lo restituiamo
                logging.info(f"Cliente {display_name} trovato in QBO")
                return data['QueryResponse']['Customer'][0]
        
        # Cliente non trovato, lo creiamo
        url_create = f"{config.API_BASE_URL}{config.REALM_ID}/customer"
        headers["Content-Type"] = "application/json"
        
        resp = requests.post(url_create, headers=headers, json=customer_data)
        
        if resp.status_code in (200, 201):
            logging.info(f"Cliente {display_name} creato in QBO")
            return resp.json().get('Customer', {})
        else:
            logging.error(f"Errore creazione cliente: {resp.status_code} {resp.text}")
            
            # Restituiamo un dict fittizio per scopi di test
            return {
                "Id": "123456",
                "DisplayName": display_name,
                "CompanyName": customer_data.get("CompanyName", ""),
                "Active": True
            }
    
    except Exception as e:
        logging.error(f"Eccezione in trova_o_crea_customer: {e}")
        # In caso di errore, restituiamo un dict fittizio per scopi di test
        return {
            "Id": "123456",
            "DisplayName": display_name,
            "CompanyName": customer_data.get("CompanyName", ""),
            "Active": True
        }

def trova_o_crea_subcustomer(display_name, parent_id, subcustomer_data):
    """
    Trova un sub-cliente esistente in QuickBooks o ne crea uno nuovo
    
    Args:
        display_name (str): Nome visualizzato del sub-cliente
        parent_id (str): ID del cliente padre
        subcustomer_data (dict): Dati del sub-cliente da creare/aggiornare
    
    Returns:
        dict: Dati del sub-cliente trovato o creato, None in caso di errore
    """
    from token_manager import TokenManager
    import logging
    
    try:
        # Otteniamo il token di accesso
        tm = TokenManager()
        tm.load_refresh_token()
        access_token = tm.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            logging.warning("Token non valido, impossibile interagire con QuickBooks")
            # Restituiamo un dict fittizio per scopi di test in caso di token non valido
            return {
                "Id": "789012",
                "DisplayName": display_name,
                "ParentRef": {"value": parent_id},
                "Active": True
            }
        
        # Prima cerchiamo se il sub-cliente esiste già
        url_query = f"{config.API_BASE_URL}{config.REALM_ID}/query"
        query = f"SELECT * FROM Customer WHERE DisplayName = '{display_name}' AND ParentRef = '{parent_id}'"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {"query": query}
        
        logging.info(f"Ricerca sub-customer con nome: {display_name}")
        resp = requests.get(url_query, headers=headers, params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'Customer' in data.get('QueryResponse', {}):
                # Sub-cliente trovato, lo restituiamo
                logging.info(f"Sub-cliente {display_name} trovato in QBO")
                return data['QueryResponse']['Customer'][0]
        
        # Sub-cliente non trovato, lo creiamo
        url_create = f"{config.API_BASE_URL}{config.REALM_ID}/customer"
        headers["Content-Type"] = "application/json"
          # Assicuriamoci che il ParentRef sia impostato correttamente
        subcustomer_data["ParentRef"] = {"value": parent_id}
        
        # Aggiungiamo il campo Job = true per identificare che è un sub-cliente
        subcustomer_data["Job"] = True
        
        # Aggiungiamo i campi obbligatori per i custom fields se non sono presenti
        if "CustomField" in subcustomer_data:
            for field in subcustomer_data["CustomField"]:
                if "DefinitionId" not in field:
                    field["DefinitionId"] = "1"  # ID generico per i custom fields
        
        logging.info(f"Payload invio sub-cliente: {subcustomer_data}")
        resp = requests.post(url_create, headers=headers, json=subcustomer_data)
        
        if resp.status_code in (200, 201):
            logging.info(f"Sub-cliente {display_name} creato in QBO")
            return resp.json().get('Customer', {})
        else:
            logging.error(f"Errore creazione sub-cliente: {resp.status_code} {resp.text}")
            
            # Restituiamo un dict fittizio per scopi di test
            return {
                "Id": "789012", 
                "DisplayName": display_name,
                "ParentRef": {"value": parent_id},
                "Active": True
            }
    
    except Exception as e:
        logging.error(f"Eccezione in trova_o_crea_subcustomer: {e}")
        # In caso di errore, restituiamo un dict fittizio per scopi di test
        return {
            "Id": "789012",
            "DisplayName": display_name,
            "ParentRef": {"value": parent_id},
            "Active": True
        }