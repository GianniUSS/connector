import requests
import config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from token_manager import token_manager
import json
import os

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
    # Validazione: display_name obbligatorio
    if not display_name or not str(display_name).strip():
        # Log dettagliato per debug
        project_id = customer_data.get('project_id') or customer_data.get('ProjectId')
        customer_id = customer_data.get('customer_id') or customer_data.get('CustomerId')
        project_name = customer_data.get('project_name') or customer_data.get('ProjectName')
        import logging
        logging.error(f"DisplayName mancante o vuoto: impossibile creare o cercare customer su QuickBooks | project_id={project_id} | customer_id={customer_id} | project_name={project_name} | customer_data={json.dumps(customer_data, ensure_ascii=False)}")
        return None
    try:
        # Otteniamo il token di accesso
        token_manager.load_refresh_token()
        access_token = token_manager.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            logging.warning("Token non valido, impossibile interagire con QuickBooks")
            return None
        
        # Prima cerchiamo se il cliente esiste già
        url_query = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
        query = f"SELECT * FROM Customer WHERE DisplayName = '{display_name}'"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        params = {"query": query}
        import logging
        logging.info(f"Ricerca customer con nome: {display_name}")
        resp = requests.get(url_query, headers=headers, params=params)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'Customer' in data.get('QueryResponse', {}):
                # Cliente trovato, lo restituiamo
                logging.info(f"Cliente {display_name} trovato in QBO")
                return data['QueryResponse']['Customer'][0]
        
        # Cliente non trovato, lo creiamo
        url_create = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/customer"
        headers["Content-Type"] = "application/json"
        customer_payload = clean_customer_payload(customer_data)
        logging.info(f"Payload invio customer: {json.dumps(customer_payload, ensure_ascii=False)}")
        resp = requests.post(url_create, headers=headers, json=customer_payload)
        
        if resp.status_code in (200, 201):
            logging.info(f"Cliente {display_name} creato in QBO")
            return resp.json().get('Customer', {})
        else:
            # Gestione errore 6240 (Duplicate Name Exists Error)
            try:
                err_json = resp.json()
                errors = err_json.get("Fault", {}).get("Error", [])
                for err in errors:
                    if err.get("code") == "6240" and "Duplicate Name Exists" in err.get("Message", ""):
                        logging.warning(f"Duplicate Name Exists Error per {display_name}, provo a recuperare il customer esistente con query 'strippata'")
                        # Query di recupero con DisplayName ripulito
                        query2 = f"SELECT * FROM Customer WHERE DisplayName = '{display_name.strip()}'"
                        params2 = {"query": query2}
                        resp2 = requests.get(url_query, headers=headers, params=params2)
                        if resp2.status_code == 200:
                            data2 = resp2.json()
                            customers2 = data2.get('QueryResponse', {}).get('Customer', [])
                            if customers2:
                                logging.info(f"Customer {display_name} recuperato dopo errore 6240 (ID: {customers2[0].get('Id')})")
                                return customers2[0]
                        logging.error(f"Customer duplicato ma non trovato nemmeno con query ripulita")
                        break
            except Exception as e2:
                logging.error(f"Errore parsing errore duplicato customer: {e2}")
            logging.error(f"Errore creazione cliente: {resp.status_code} {resp.text}")
            return None
    
    except Exception as e:
        logging.error(f"Eccezione in trova_o_crea_customer: {e}")
        return None

def trova_o_crea_subcustomer(display_name, parent_id, subcustomer_data):
    """
    Trova un sub-cliente esistente in QuickBooks o ne crea uno nuovo
    (versione con strategie multiple per gestire apostrofi)
    """
    import logging
    
    try:
        token_manager.load_refresh_token()
        access_token = token_manager.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            logging.warning("Token non valido, impossibile interagire con QuickBooks")
            return {
                "Id": "789012",
                "DisplayName": display_name,
                "ParentRef": {"value": parent_id},
                "Active": True
            }
        
        url_query = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        # Strategia 1: Query con escape apostrofi
        safe_display_name = display_name.replace("'", "''") if display_name else display_name
        query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_display_name}'"
        params = {"query": query}
        
        logging.info(f"[QBO][SUB-CUSTOMER] Cerco sub-customer con DisplayName: '{display_name}' (escaped: '{safe_display_name}')")
        resp = requests.get(url_query, headers=headers, params=params)
        
        # Se la query diretta fallisce per parsing, provo strategie alternative
        if resp.status_code == 400 and 'Error parsing query' in resp.text:
            logging.warning(f"[QBO][SUB-CUSTOMER] Query con escape fallita per parsing. Provo query senza escape...")
            
            # Strategia 2: Query senza escape degli apostrofi
            query_no_escape = f"SELECT * FROM Customer WHERE DisplayName = '{display_name}'"
            params_no_escape = {"query": query_no_escape}
            resp_alt = requests.get(url_query, headers=headers, params=params_no_escape)
            
            if resp_alt.status_code == 200:
                data_alt = resp_alt.json()
                customers_alt = data_alt.get('QueryResponse', {}).get('Customer', [])
                if customers_alt:
                    # Filtro per parent_id se necessario
                    matching_customers = [c for c in customers_alt if c.get('ParentRef', {}).get('value') == parent_id]
                    if matching_customers:
                        logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato con query senza escape, ID {matching_customers[0].get('Id')}")
                        return matching_customers[0]
                    elif len(customers_alt) == 1:
                        logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato con query senza escape (unico), ID {customers_alt[0].get('Id')}")
                        return customers_alt[0]
            
            # Strategia 3: Workaround completo - recupera tutti i sub-customer e filtra in Python
            logging.warning(f"[QBO][SUB-CUSTOMER] Anche query senza escape fallita. Provo workaround: recupero tutti i sub-customer (Job=true) e filtro in Python...")
            query_all = "SELECT * FROM Customer WHERE Job = true"
            params_all = {"query": query_all}
            resp_all = requests.get(url_query, headers=headers, params=params_all)
            
            if resp_all.status_code == 200:
                data_all = resp_all.json()
                customers_all = data_all.get('QueryResponse', {}).get('Customer', [])
                logging.info(f"[QBO][SUB-CUSTOMER] Recuperati {len(customers_all)} sub-customer totali, filtro per DisplayName='{display_name}' e ParentRef.value='{parent_id}'")
                
                for c in customers_all:
                    customer_display_name = c.get('DisplayName', '')
                    customer_parent_ref = c.get('ParentRef', {}).get('value', '')
                    logging.debug(f"[QBO][SUB-CUSTOMER] Controllo: DisplayName='{customer_display_name}', ParentRef='{customer_parent_ref}'")
                    if customer_display_name == display_name and customer_parent_ref == parent_id:
                        logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato tramite workaround, ID {c.get('Id')}")
                        return c
                
                logging.warning(f"[QBO][SUB-CUSTOMER] Nessun sub-customer trovato tramite workaround per DisplayName='{display_name}' e ParentRef='{parent_id}'")
            else:
                logging.error(f"[QBO][SUB-CUSTOMER] Workaround fallito: errore query all sub-customer: status {resp_all.status_code} - {resp_all.text}")
                
        elif resp.status_code == 200:
            # Query riuscita, controllo i risultati
            data = resp.json()
            customers = data.get('QueryResponse', {}).get('Customer', [])
            if customers:
                # Filtro per parent_id se ho più risultati
                matching_customers = [c for c in customers if c.get('ParentRef', {}).get('value') == parent_id]
                if matching_customers:
                    if len(matching_customers) > 1:
                        logging.warning(f"[QBO][SUB-CUSTOMER] Trovati {len(matching_customers)} sub-customer con lo stesso DisplayName e ParentRef: '{display_name}'. Restituisco il primo con ID {matching_customers[0].get('Id')}")
                    else:
                        logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato in QBO con ID {matching_customers[0].get('Id')}")
                    return matching_customers[0]
                elif len(customers) == 1:
                    # Se c'è un solo risultato, probabilmente è quello giusto
                    logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato (unico risultato), ID {customers[0].get('Id')}")
                    return customers[0]
                else:
                    logging.warning(f"[QBO][SUB-CUSTOMER] Trovati {len(customers)} customer con DisplayName '{display_name}' ma nessuno con ParentRef='{parent_id}' (procedo con creazione)")
            else:
                logging.info(f"[QBO][SUB-CUSTOMER] Nessun sub-customer trovato per '{display_name}' (procedo con creazione)")
        else:
            logging.error(f"[QBO][SUB-CUSTOMER] Errore query sub-customer: status {resp.status_code} - {resp.text}")
        
        # Creazione sub-cliente
        url_create = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/customer"
        headers["Content-Type"] = "application/json"
        subcustomer_data["ParentRef"] = {"value": parent_id}
        subcustomer_data["Job"] = True
        if "CustomField" in subcustomer_data:
            for field in subcustomer_data["CustomField"]:
                if "DefinitionId" not in field:
                    field["DefinitionId"] = "1"
        
        logging.info(f"[QBO][SUB-CUSTOMER] Invio richiesta creazione sub-customer: {subcustomer_data}")
        resp = requests.post(url_create, headers=headers, json=subcustomer_data)
        
        if resp.status_code in (200, 201):
            customer = resp.json().get('Customer', {})
            logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' creato in QBO con ID {customer.get('Id')}")
            return customer
        else:
            # Gestione errore 6000 (already using this name)
            try:
                logging.error(f"[QBO][SUB-CUSTOMER] Errore creazione sub-customer: status {resp.status_code} - {resp.text}")
                err_json = resp.json()
                errors = err_json.get("Fault", {}).get("Error", [])
                
                for err in errors:
                    if (err.get("code") == "6000" and "already using this name" in err.get("Detail", "")):
                        logging.warning(f"[QBO][SUB-CUSTOMER] Sub-customer già esistente con nome '{display_name}'. Provo a recuperare l'ID tramite strategie di fallback...")
                        
                        # Strategia fallback 1: Query diretta con escape
                        safe_display_name_fallback = display_name.replace("'", "''") if display_name else display_name
                        query_fallback = f"SELECT * FROM Customer WHERE DisplayName = '{safe_display_name_fallback}'"
                        params_fallback = {"query": query_fallback}
                        logging.info(f"[QBO][SUB-CUSTOMER] Query fallback per recupero ID: {query_fallback}")
                        resp3 = requests.get(url_query, headers=headers, params=params_fallback)
                        
                        if resp3.status_code == 200:
                            data3 = resp3.json()
                            customers3 = data3.get('QueryResponse', {}).get('Customer', [])
                            if customers3:
                                # Filtro per parent_id se ho più risultati
                                matching_customers = [c for c in customers3 if c.get('ParentRef', {}).get('value') == parent_id]
                                if matching_customers:
                                    customer_found = matching_customers[0]
                                    logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato con fallback query diretta, ID {customer_found.get('Id')}")
                                    return customer_found
                                elif len(customers3) == 1:
                                    # Se c'è un solo risultato, probabilmente è quello giusto
                                    customer_found = customers3[0]
                                    logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato con fallback (unico risultato), ID {customer_found.get('Id')}")
                                    return customer_found
                        
                        # Strategia fallback 2: Se query diretta fallisce, provo workaround completo
                        if resp3.status_code != 200 or not customers3:
                            logging.warning(f"[QBO][SUB-CUSTOMER] Query diretta fallita, provo workaround completo...")
                            query_all_fallback = "SELECT * FROM Customer WHERE Job = true"
                            params_all_fallback = {"query": query_all_fallback}
                            resp_all_fallback = requests.get(url_query, headers=headers, params=params_all_fallback)
                            
                            if resp_all_fallback.status_code == 200:
                                data_all_fallback = resp_all_fallback.json()
                                customers_all_fallback = data_all_fallback.get('QueryResponse', {}).get('Customer', [])
                                logging.info(f"[QBO][SUB-CUSTOMER] Fallback completo: recuperati {len(customers_all_fallback)} sub-customer, filtro per DisplayName='{display_name}' e ParentRef='{parent_id}'")
                                
                                for c in customers_all_fallback:
                                    customer_display_name = c.get('DisplayName', '')
                                    customer_parent_ref = c.get('ParentRef', {}).get('value', '')
                                    if customer_display_name == display_name and customer_parent_ref == parent_id:
                                        logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato tramite fallback completo, ID {c.get('Id')}")
                                        return c
                                
                                logging.error(f"[QBO][SUB-CUSTOMER] Sub-customer duplicato ma non trovato nemmeno con fallback completo")
                            else:
                                logging.error(f"[QBO][SUB-CUSTOMER] Errore fallback completo: status {resp_all_fallback.status_code} - {resp_all_fallback.text}")
                        else:
                            logging.error(f"[QBO][SUB-CUSTOMER] Errore query fallback diretta: status {resp3.status_code} - {resp3.text}")
                        return None
                        
            except Exception as e2:
                logging.error(f"[QBO][SUB-CUSTOMER] Errore parsing errore duplicato sub-customer: {e2}")
            
            logging.error(f"[QBO][SUB-CUSTOMER] Errore creazione sub-cliente: {resp.status_code} {resp.text}")
            return None
            
    except Exception as e:
        logging.error(f"[QBO][SUB-CUSTOMER] Eccezione in trova_o_crea_subcustomer: {e}")
        return None

def clean_customer_payload(data):
    allowed_fields = {
        "DisplayName", "CompanyName", "PrimaryEmailAddr", "PrimaryPhone", "BillAddr", "Taxable"
    }
    cleaned = {k: v for k, v in data.items() if k in allowed_fields and v not in ("", None, {})}
    # Rimuovi PrimaryPhone se vuoto
    if "PrimaryPhone" in cleaned and not cleaned["PrimaryPhone"].get("FreeFormNumber"):
        cleaned.pop("PrimaryPhone")
    # Rimuovi BillAddr se tutti i campi sono vuoti
    if "BillAddr" in cleaned:
        if not any(v for v in cleaned["BillAddr"].values()):
            cleaned.pop("BillAddr")
    return cleaned

_qb_import_status_lock = threading.Lock()
_qb_import_status_path = os.path.join(os.path.dirname(__file__), 'qb_import_status.json')

def load_qb_import_status():
    """Carica lo stato di importazione QB da file JSON."""
    with _qb_import_status_lock:
        if not os.path.exists(_qb_import_status_path):
            return {}
        try:
            with open(_qb_import_status_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

def save_qb_import_status(status_dict):
    """Salva lo stato di importazione QB su file JSON."""
    with _qb_import_status_lock:
        with open(_qb_import_status_path, 'w', encoding='utf-8') as f:
            json.dump(status_dict, f, ensure_ascii=False, indent=2)

def set_qb_import_status(project_id, status, message=None):
    """Aggiorna lo stato di importazione per un progetto."""
    status_dict = load_qb_import_status()
    status_dict[str(project_id)] = {
        'status': status,
        'message': message or '',
        'timestamp': datetime.now().isoformat(timespec='seconds')
    }
    save_qb_import_status(status_dict)

def get_qb_import_status(project_id):
    """Restituisce lo stato di importazione per un progetto."""
    status_dict = load_qb_import_status()
    return status_dict.get(str(project_id), None)
