import requests
import config
import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
from token_manager import token_manager
import json
import os

# Import funzioni da rentman_api per la modalità normale
from rentman_api import process_project, get_all_statuses

# 🚀 NUOVO: Sistema di logging configurabile
LOG_LEVEL = os.getenv('RENTMAN_LOG_LEVEL', 'INFO')  # DEBUG, INFO, WARNING, ERROR
VERBOSE_MODE = LOG_LEVEL == 'DEBUG'

def log_info(message):
    """Log controllabile per messaggi informativi"""
    if VERBOSE_MODE:
        print(f"[INFO] {message}")

def log_debug(message):
    """Log controllabile per messaggi di debug"""
    if VERBOSE_MODE:
        print(f"[DEBUG] {message}")

def log_warning(message):
    """Log sempre visibile per warning"""
    print(f"[WARN] {message}")

def log_error(message):
    """Log sempre visibile per errori"""
    print(f"[ERROR] {message}")

# Cache globali per ottimizzazione
_projecttype_cache = {}
_status_cache = {}
_cache_lock = threading.Lock()

# Cache thread-safe per responsabili (come in rentman_api.py)
_manager_cache = {}
_manager_cache_lock = threading.Lock()

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

def get_project_subprojects_fast(project_ids, headers):
    """Recupera i subprojects di uno o più progetti (accodando i parametri project nella query) e logga sinteticamente."""
    url = f"{config.REN_BASE_URL}/subprojects"
    # Permetti sia singolo id che lista
    if isinstance(project_ids, (str, int)):
        project_ids = [project_ids]
    params = []
    for pid in project_ids:
        params.append(("project", pid))
    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        log_debug(f"[SUBPROJECTS] GET {url} params={params} status={response.status_code}")
        if response.ok:
            data = response.json().get('data', [])
            if isinstance(data, dict):
                data = [data]
            log_debug(f"[SUBPROJECTS] Trovati {len(data)} subprojects per {len(project_ids)} progetti")
            for sub in data:
                pid = sub.get('project')
                status = sub.get('status')
                order = sub.get('order')
                sub_id = sub.get('id')
                # Il valore del subproject è project_total_price, non quello del progetto principale
                value = sub.get('project_total_price')
                log_debug(f"  - Subproject ID {sub_id} (project {pid}, order {order}): status={status}, value={value}")
            return data
        elif response.status_code == 404:
            log_debug(f"[SUBPROJECTS] Nessun subproject trovato per {project_ids}")
            return []
        else:
            log_error(f"[SUBPROJECTS] Errore HTTP {response.status_code} per {project_ids}")
            return []
    except Exception as e:
        log_error(f"[SUBPROJECTS] Exception: {e}")
        return []

def get_project_status_paginated(project_id, headers, status_map, main_project=None):
    """ 
    Versione ALLINEATA alla modalità normale (Fast API v2)
    FILTRO IDENTICO: Solo subprojects con in_financial=True
    """
    subprojects = get_project_subprojects_fast(project_id, headers)
    
    # LOGICA IDENTICA ALLA MODALITÀ NORMALE: filtra SOLO subprojects con in_financial=True
    if subprojects:
        # 🎯 FIX: Filtra solo subprojects con in_financial=True (come Fast API v2)
        financial_subs = [s for s in subprojects if s.get('in_financial') is True]
        
        if financial_subs:
            # Seleziona quello con order più basso tra quelli finanziari
            subproject_principale = min(financial_subs, key=lambda s: s.get('order', 9999))
            status_path = subproject_principale.get('status')
            status_id = extract_id_from_path(status_path)
            value = subproject_principale.get('project_total_price')
            logging.info(f"[PROGETTO {project_id}] PAGINATA - Subproject finanziario: status_id={status_id}, value={value}, order={subproject_principale.get('order')}")
            if status_id and status_id in status_map:
                return status_map[status_id]
        else:
            logging.info(f"[PROGETTO {project_id}] PAGINATA - Nessun subproject con in_financial=True trovato")
    
    # Se nessun subproject finanziario valido, prova a usare lo status del progetto principale
    if main_project:
        main_status_path = main_project.get('status')
        status_id = extract_id_from_path(main_status_path)
        value = main_project.get('project_total_price')
        logging.info(f"[PROGETTO {project_id}] PAGINATA - Nessun subproject valido, status_id principale={status_id}, value principale={value}")
        if status_id and status_id in status_map:
            return status_map[status_id]
    
    return "Concept"  # Default IDENTICO alla modalità normale

def process_project_paginated(project_data, headers, status_map, start_dt, end_dt, debug_count):
    """ Processa un singolo progetto per la modalità PAGINATA con logica status dedicata """
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
        
        # 🎯 USA LA LOGICA STATUS SPECIFICA PER MODALITÀ PAGINATA
        project_id = p.get('id')
        project_status = get_project_status_paginated(project_id, headers, status_map, main_project=p)
          # Debug migliorato
        if debug_count[0] < 3:
            log_debug(f"🔍 Debug progetto {project_id}:")
            log_debug(f"  📝 Raw number field: {repr(p.get('number'))}")
            log_debug(f"  🔢 Number type: {type(p.get('number'))}")
            log_debug(f"  📄 Name: '{p.get('name')}'")
            log_debug(f"  📊 Status: '{project_status}'")
            log_debug(f"  🏷️ Project type ID: {project_type_id}")
            debug_count[0] += 1
        
        # Conversione numero con debug extra
        raw_number = p.get("number")
        if raw_number is not None:
            converted_number = str(raw_number)
            if debug_count[0] <= 3:
                log_debug(f"  ✅ Converted number: '{converted_number}'")
        else:
            converted_number = "N/A"
            if debug_count[0] <= 3:
                log_debug(f"  ❌ Number is None!")
        
        # Estrazione robusta del valore (come in rentman_api.py)
        project_value = None
        subprojects = get_project_subprojects_fast(project_id, headers)
        if subprojects:
            subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
            project_value = subproject_principale.get('project_total_price')
            log_debug(f"[PROGETTO {project_id}] Valore dal subproject principale: {project_value}")
        if project_value is None or str(project_value).strip() == '':
            project_value = p.get('project_total_price')
            log_debug(f"[PROGETTO {project_id}] Valore dal progetto principale: {project_value}")
        try:
            formatted_value = '{:.2f}'.format(float(project_value))
        except (ValueError, TypeError):
            formatted_value = '0.00'
        
        # --- Recupero dati responsabile progetto (come in rentman_api.py) ---
        manager_name = None
        manager_email = None
        account_manager_path = p.get('account_manager')
        if account_manager_path:
            manager_id = extract_id_from_path(account_manager_path)
            if manager_id:
                with _manager_cache_lock:
                    if manager_id in _manager_cache:
                        manager_name, manager_email = _manager_cache[manager_id]
                    else:
                        try:
                            crew_url = f"{config.REN_BASE_URL}/crew/{manager_id}"
                            crew_resp = requests.get(crew_url, headers=headers, timeout=5)
                            if crew_resp.ok:
                                crew_data = crew_resp.json().get('data', {})
                                manager_name = crew_data.get('name') or crew_data.get('displayname')
                                manager_email = crew_data.get('email') or crew_data.get('email_1')
                                _manager_cache[manager_id] = (manager_name, manager_email)
                                if not manager_name or not manager_email:
                                    log_warning(f"[WARN] Responsabile NON valorizzato per progetto {project_id} (manager_id={manager_id}) - crew_data: {crew_data}")
                            else:
                                log_warning(f"[WARN] Errore HTTP recuperando responsabile progetto {project_id} (manager_id={manager_id}): {crew_resp.status_code} - {crew_resp.text}")
                        except Exception as e:
                            log_warning(f"[WARN] Errore recuperando responsabile progetto {manager_id}: {e}")
            else:
                log_warning(f"[WARN] account_manager_path presente ma manager_id non estratto per progetto {project_id} (path: {account_manager_path})")
        else:
            log_warning(f"[WARN] Nessun account_manager per progetto {project_id}")
        
        return {
            "id": project_id,
            "number": converted_number,
            "name": p.get("name") or "",
            "status": project_status,
            "equipment_period_from": period_start[:10] if period_start else None,
            "equipment_period_to": period_end[:10] if period_end else None,
            "project_type_id": project_type_id,
            "project_type_name": "",  # Recuperato dopo per velocità
            "project_value": formatted_value,
            "manager_name": manager_name,
            "manager_email": manager_email
        }
        
    except Exception as e:
        print(f"❌ Errore processando progetto {p.get('id', 'unknown')}: {e}")
        return None

def list_projects_by_date(from_date, to_date):
    log_debug("🚀 Avvio recupero progetti ottimizzato...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti con approccio completo (standard + progetti mancanti)
    url = f"{config.REN_BASE_URL}/projects"
    
    log_debug(f"🔄 Recupero progetti con chiamata standard...")
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    
    standard_projects = response.json().get('data', [])
    log_debug(f"📄 Progetti standard recuperati: {len(standard_projects)}")    # Aggiungi progetti mancanti noti con chiamate dirette
    missing_project_ids = [3120, 3299]  # IDs per numeri 3143 e 3322
    additional_projects = []
    log_debug(f"🔍 Recupero progetti mancanti: {missing_project_ids}")
    for project_id in missing_project_ids:
        try:
            project_url = f"{config.REN_BASE_URL}/projects/{project_id}"
            response = requests.get(project_url, headers=headers)
            
            if response.ok:
                project = response.json().get('data', {})
                if project:
                    additional_projects.append(project)
                    log_debug(f"  ✅ Aggiunto progetto {project_id} (numero {project.get('number')})")
            else:
                log_debug(f"  ❌ Progetto {project_id} non trovato: {response.status_code}")
        except Exception as e:
            log_debug(f"  ❌ Errore progetto {project_id}: {e}")
    
    projects = standard_projects + additional_projects
    log_debug(f"📊 Progetti totali: {len(projects)} (standard: {len(standard_projects)}, aggiunti: {len(additional_projects)})")
    log_debug(f"📋 Progetti totali recuperati: {len(projects)}")
    
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    # Processa progetti con threading per velocità
    filtered = []
    debug_count = [0]  # Lista per reference mutabile
    
    log_debug(f"⏳ Filtraggio progetti per periodo {from_date} - {to_date}...")
    
    # Processa sequenzialmente per ora (per debug)
    for p in projects:
        result = process_project(p, headers, status_map, start_dt, end_dt, debug_count)
        if result:
            filtered.append(result)    
    log_debug(f"✅ Progetti filtrati: {len(filtered)}")
    
    # Recupera project type names per i progetti filtrati (in parallelo)
    if filtered:
        log_debug("🏷️ Recupero nomi project types...")
        unique_type_ids = set(p['project_type_id'] for p in filtered if p['project_type_id'])
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            type_name_futures = {
                type_id: executor.submit(get_projecttype_name_cached, type_id, headers)
                for type_id in unique_type_ids            }
            
            # Aggiorna i project type names
            for project in filtered:
                type_id = project['project_type_id']
                if type_id and type_id in type_name_futures:
                    try:
                        project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                    except:
                        project['project_type_name'] = ""
    
    log_debug(f"🎉 Completato! Restituiti {len(filtered)} progetti")
    return filtered

def list_projects_by_date_paginated(from_date, to_date, page_size=20):
    """
    Versione paginata del caricamento progetti per migliorare performance
    
    Args:
        from_date (str): Data inizio nel formato YYYY-MM-DD
        to_date (str): Data fine nel formato YYYY-MM-DD  
        page_size (int): Numero di progetti per pagina (default 20)
    
    Returns:
        Generator: Yield pgetti filtrati    """
    log_debug(f"🚀 Avvio recupero progetti paginato (pagine da {page_size})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map (una volta sola)
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti con approccio completo (standard + progetti mancanti)
    url = f"{config.REN_BASE_URL}/projects"
    
    log_debug(f"🔄 Recupero progetti con chiamata standard...")
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    
    standard_projects = response.json().get('data', [])
    log_debug(f"📄 Progetti standard recuperati: {len(standard_projects)}")
    
    # Aggiungi progetti mancanti noti con chiamate dirette
    missing_project_ids = [3120, 3299]  # IDs per numeri 3143 e 3322
    additional_projects = []
    
    log_debug(f"🔍 Recupero progetti mancanti: {missing_project_ids}")
    for project_id in missing_project_ids:
        try:
            project_url = f"{config.REN_BASE_URL}/projects/{project_id}"
            response = requests.get(project_url, headers=headers)
            
            if response.ok:
                project = response.json().get('data', {})
                if project:
                    additional_projects.append(project)
                    log_debug(f"  ✅ Aggiunto progetto {project_id} (numero {project.get('number')})")
            else:
                log_debug(f"  ❌ Progetto {project_id} non trovato: {response.status_code}")
        except Exception as e:
            log_debug(f"  ❌ Errore progetto {project_id}: {e}")
    
    all_projects = standard_projects + additional_projects
    log_debug(f"📊 Progetti totali: {len(all_projects)} (standard: {len(standard_projects)}, aggiunti: {len(additional_projects)})")
    
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
      # Pre-filtra progetti per date
    log_debug(f"⏳ Pre-filtro progetti per periodo {from_date} - {to_date}...")
    date_filtered_projects = []
    
    for p in all_projects:
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        
        if not period_start or not period_end:
            continue
            
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
            # Usa la stessa logica della modalità normale (corretta)
            if not (pe < start_dt or ps > end_dt):
                date_filtered_projects.append(p)
        except Exception:
            continue
    
    log_debug(f"✅ Progetti nel periodo: {len(date_filtered_projects)}")
    # Processa progetti a pagine
    debug_count = [0]
    total_processed = 0
    
    for i in range(0, len(date_filtered_projects), page_size):
        page_projects = date_filtered_projects[i:i + page_size]
        page_num = (i // page_size) + 1
        
        log_debug(f"📄 Processando pagina {page_num} ({len(page_projects)} progetti)...")
        
        page_results = []
        for p in page_projects:
            result = process_project_paginated(p, headers, status_map, start_dt, end_dt, debug_count)
            if result:
                page_results.append(result)
                total_processed += 1
        
        # Recupera project type names per questa pagina
        if page_results:
            unique_type_ids = set(proj['project_type_id'] for proj in page_results if proj['project_type_id'])
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                type_name_futures = {
                    type_id: executor.submit(get_projecttype_name_cached, type_id, headers)
                    for type_id in unique_type_ids
                }
                
                # Aggiorna i project type names
                for project in page_results:
                    type_id = project['project_type_id']
                    if type_id and type_id in type_name_futures:
                        try:
                            project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                        except:
                            project['project_type_name'] = ""
        
        log_debug(f"✅ Pagina {page_num} completata: {len(page_results)} progetti processati")
        
        # Yield la pagina corrente
        yield {
            'page': page_num,
            'projects': page_results,
            'total_in_page': len(page_results),
            'total_processed': total_processed,
            'has_more': (i + page_size) < len(date_filtered_projects)
        }
    
    log_debug(f"🎉 Paginazione completata! {total_processed} progetti totali processati")

def list_projects_by_date_paginated_full(from_date, to_date, page_size=20):
    """
    Versione che restituisce tutti i progetti paginati come lista completa
    """
    all_projects = []
    
    for page_data in list_projects_by_date_paginated(from_date, to_date, page_size):
        all_projects.extend(page_data['projects'])
        log_debug(f"📊 Progresso: {page_data['total_processed']} progetti caricati...")

    # Applica filtro stati DOPO il processamento - ALLINEATO con modalità normale (SOLO stati validi)
    log_debug(f"⏳ Applicando filtro stati finale su {len(all_projects)} progetti processati...")

    # CRITERI SPECIFICI: solo stati dei 9 progetti mostrati in Rentman (05/06/2025)
    stati_validi = {
        # Stati confermati/operativi (dai progetti mostrati)
        'confermato', 'confirmed', 
        'in location', 'on location',
        'rientrato', 'returned',
        # Stati speciali per progetti 3143 e 3322 (combinati)
        'in location / annullato', 'on location / cancelled',
        'rientrato / concept', 'returned / concept'
    }
    
    # Debug: mostra stati prima del filtro
    stati_presenti = set()
    for p in all_projects:
        stati_presenti.add(p.get('status', 'NESSUNO'))
    log_debug(f"🔍 Stati presenti prima del filtro finale: {sorted(stati_presenti)}")
      # Filtra SOLO i progetti con stati validi (rimuovendo logica "target progetti")
    progetti_validi = []
    
    for p in all_projects:
        status = p.get('status', '').lower().strip()
        if status in stati_validi:
            progetti_validi.append(p)
            log_debug(f"  ✅ VALIDO - Progetto {p.get('id')} con status '{p.get('status')}'")
        else:
            log_debug(f"  🚫 ESCLUSO - Progetto {p.get('id')} con status '{p.get('status')}' (non negli stati validi)")
    
    log_debug(f"📊 Progetti validi finali: {len(progetti_validi)}")
    
    # Risultato finale: SOLO progetti con stati validi
    return progetti_validi

# Funzione per svuotare le cache se necessario
def clear_cache():
    """ Svuota le cache per forzare il refresh """
    global _projecttype_cache, _status_cache, _manager_cache
    with _cache_lock:
        _projecttype_cache.clear()
        _status_cache.clear()
    with _manager_cache_lock:
        _manager_cache.clear()
    print("🧹 Cache svuotata (inclusa cache manager)")

# Funzioni per la gestione dei clienti QuickBooks
def trova_o_crea_customer(display_name, customer_data):
    """
    Trova un cliente esistente in QuickBooks o ne crea uno nuovo
    (versione con strategie multiple per gestire apostrofi, spazi e inconsistenze)
    
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
        
        # URL e headers per le query
        url_query = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        import logging
        logging.info(f"[QBO][CUSTOMER] Ricerca customer con nome: {display_name}")
        
        # Strategia 1: Query diretta con escape apostrofi
        safe_display_name = display_name.replace("'", "''") if display_name else display_name
        query = f"SELECT * FROM Customer WHERE DisplayName = '{safe_display_name}'"
        params = {"query": query}
        
        logging.info(f"[QBO][CUSTOMER] Query diretta (escaped): {query}")
        resp = requests.get(url_query, headers=headers, params=params)
        
        # Se la query diretta fallisce per parsing, provo strategie alternative
        if resp.status_code == 400 and 'Error parsing query' in resp.text:
            logging.warning(f"[QBO][CUSTOMER] Query con escape fallita per parsing. Provo query senza escape...")
            
            # Strategia 2: Query senza escape degli apostrofi
            query_no_escape = f"SELECT * FROM Customer WHERE DisplayName = '{display_name}'"
            params_no_escape = {"query": query_no_escape}
            resp = requests.get(url_query, headers=headers, params=params_no_escape)
            
            if resp.status_code == 200:
                data = resp.json()
                customers = data.get('QueryResponse', {}).get('Customer', [])
                if customers:
                    # Filtro per escludere sub-customer (che hanno ParentRef)
                    main_customers = [c for c in customers if not c.get('ParentRef')]
                    if main_customers:
                        logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato con query senza escape, ID {main_customers[0].get('Id')}")
                        return main_customers[0]
                    elif len(customers) == 1 and not customers[0].get('ParentRef'):
                        logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato con query senza escape (unico), ID {customers[0].get('Id')}")
                        return customers[0]
              # Strategia 3: Workaround completo - recupera tutti i customer principali e filtra in Python
            logging.warning(f"[QBO][CUSTOMER] Anche query senza escape fallita. Provo workaround: recupero tutti i customer principali e filtro in Python...")
            
            # Prima prova con query LIKE per una ricerca più efficace
            query_like = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{display_name}%' MAXRESULTS 1000"
            params_like = {"query": query_like}
            resp_like = requests.get(url_query, headers=headers, params=params_like)
            
            if resp_like.status_code == 200:
                data_like = resp_like.json()
                customers_like = data_like.get('QueryResponse', {}).get('Customer', [])
                logging.info(f"[QBO][CUSTOMER] Query LIKE recuperati {len(customers_like)} customer, filtro per DisplayName='{display_name}' (escludendo sub-customer)")
                
                # Usa la funzione di matching robusta per customer principali
                found_customer = find_customer_with_robust_matching(customers_like, display_name)
                if found_customer:
                    return found_customer
            
            # Se LIKE fallisce, prova query generale con MAXRESULTS
            query_all = "SELECT * FROM Customer WHERE Active = true MAXRESULTS 1000"
            params_all = {"query": query_all}
            resp_all = requests.get(url_query, headers=headers, params=params_all)
            
            if resp_all.status_code == 200:
                data_all = resp_all.json()
                customers_all = data_all.get('QueryResponse', {}).get('Customer', [])
                logging.info(f"[QBO][CUSTOMER] Recuperati {len(customers_all)} customer totali, filtro per DisplayName='{display_name}' (escludendo sub-customer)")
                
                # Usa la funzione di matching robusta per customer principali
                found_customer = find_customer_with_robust_matching(customers_all, display_name)
                if found_customer:
                    return found_customer
                
                logging.warning(f"[QBO][CUSTOMER] Nessun customer principale trovato tramite workaround per DisplayName='{display_name}'")
            else:
                logging.error(f"[QBO][CUSTOMER] Workaround fallito: errore query all customer: status {resp_all.status_code} - {resp_all.text}")
        elif resp.status_code == 200:
            # Query riuscita, controllo i risultati
            data = resp.json()
            customers = data.get('QueryResponse', {}).get('Customer', [])
            if customers:
                # Filtro per escludere sub-customer (che hanno ParentRef)
                main_customers = [c for c in customers if not c.get('ParentRef')]
                if main_customers:
                    if len(main_customers) > 1:
                        logging.warning(f"[QBO][CUSTOMER] Trovati {len(main_customers)} customer principali con lo stesso DisplayName: '{display_name}'. Restituisco il primo con ID {main_customers[0].get('Id')}")
                    else:
                        logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato in QBO con ID {main_customers[0].get('Id')}")
                    return main_customers[0]
                elif len(customers) == 1 and not customers[0].get('ParentRef'):
                    # Se c'è un solo risultato ed è un customer principale
                    logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (unico risultato), ID {customers[0].get('Id')}")
                    return customers[0]
                else:
                    logging.warning(f"[QBO][CUSTOMER] Trovati {len(customers)} customer con DisplayName '{display_name}' ma tutti sono sub-customer (procedo con creazione)")
            else:
                logging.info(f"[QBO][CUSTOMER] Nessun customer trovato per '{display_name}' (procedo con creazione)")
        else:
            logging.error(f"[QBO][CUSTOMER] Errore query customer: status {resp.status_code} - {resp.text}")

        # Cliente non trovato, procediamo con la creazione
        url_create = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/customer"
        headers["Content-Type"] = "application/json"
        customer_payload = clean_customer_payload(customer_data)
        logging.info(f"[QBO][CUSTOMER] Payload invio customer: {json.dumps(customer_payload, ensure_ascii=False)}")
        resp = requests.post(url_create, headers=headers, json=customer_payload)
        
        if resp.status_code in (200, 201):
            customer = resp.json().get('Customer', {})
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' creato in QBO con ID {customer.get('Id')}")
            return customer
        else:
            # Gestione errore 6240 (Duplicate Name Exists Error) con strategie multiple
            try:
                logging.error(f"[QBO][CUSTOMER] Errore creazione customer: status {resp.status_code} - {resp.text}")
                err_json = resp.json()
                errors = err_json.get("Fault", {}).get("Error", [])
                
                for err in errors:
                    if err.get("code") == "6240" and "Duplicate Name Exists" in err.get("Message", ""):
                        logging.warning(f"[QBO][CUSTOMER] Duplicate Name Exists Error per '{display_name}'. Provo strategie multiple per recuperare il customer esistente...")
                        
                        # Strategia fallback 1: Query diretta con escape
                        safe_display_name_fallback = display_name.replace("'", "''") if display_name else display_name
                        query_fallback = f"SELECT * FROM Customer WHERE DisplayName = '{safe_display_name_fallback}'"
                        params_fallback = {"query": query_fallback}
                        logging.info(f"[QBO][CUSTOMER] Query fallback per recupero ID: {query_fallback}")
                        resp3 = requests.get(url_query, headers=headers, params=params_fallback)
                        
                        if resp3.status_code == 200:
                            data3 = resp3.json()
                            customers3 = data3.get('QueryResponse', {}).get('Customer', [])
                            if customers3:
                                # Filtro per customer principali
                                main_customers = [c for c in customers3 if not c.get('ParentRef')]
                                if main_customers:
                                    customer_found = main_customers[0]
                                    logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' recuperato con fallback query diretta, ID {customer_found.get('Id')}")
                                    return customer_found
                                elif len(customers3) == 1 and not customers3[0].get('ParentRef'):
                                    # Se c'è un solo risultato ed è un customer principale
                                    customer_found = customers3[0]
                                    logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' recuperato con fallback (unico risultato), ID {customer_found.get('Id')}")
                                    return customer_found
                          # Strategia fallback 2: Workaround completo con strategie multiple
                        if resp3.status_code != 200 or not customers3:
                            logging.warning(f"[QBO][CUSTOMER] Query diretta fallita, provo workaround completo...")
                            
                            # Prova prima con LIKE
                            query_like_fallback = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{display_name}%' MAXRESULTS 1000"
                            params_like_fallback = {"query": query_like_fallback}
                            resp_like_fallback = requests.get(url_query, headers=headers, params=params_like_fallback)
                            
                            if resp_like_fallback.status_code == 200:
                                data_like_fallback = resp_like_fallback.json()
                                customers_like_fallback = data_like_fallback.get('QueryResponse', {}).get('Customer', [])
                                logging.info(f"[QBO][CUSTOMER] Fallback LIKE: recuperati {len(customers_like_fallback)} customer, filtro per DisplayName='{display_name}' (escludendo sub-customer)")
                                
                                # Usa la funzione di matching robusta
                                found_customer = find_customer_with_robust_matching(customers_like_fallback, display_name)
                                if found_customer:
                                    return found_customer
                            
                            # Se LIKE fallisce, prova query generale
                            query_all_fallback = "SELECT * FROM Customer WHERE Active = true MAXRESULTS 1000"
                            params_all_fallback = {"query": query_all_fallback}
                            resp_all_fallback = requests.get(url_query, headers=headers, params=params_all_fallback)
                            
                            if resp_all_fallback.status_code == 200:
                                data_all_fallback = resp_all_fallback.json()
                                customers_all_fallback = data_all_fallback.get('QueryResponse', {}).get('Customer', [])
                                logging.info(f"[QBO][CUSTOMER] Fallback completo: recuperati {len(customers_all_fallback)} customer, filtro per DisplayName='{display_name}' (escludendo sub-customer)")
                                
                                # Usa la funzione di matching robusta
                                found_customer = find_customer_with_robust_matching(customers_all_fallback, display_name)
                                if found_customer:
                                    return found_customer
                                
                                logging.error(f"[QBO][CUSTOMER] Customer duplicato ma non trovato nemmeno con fallback completo")
                            else:
                                logging.error(f"[QBO][CUSTOMER] Errore fallback completo: status {resp_all_fallback.status_code} - {resp_all_fallback.text}")
                        else:
                            logging.error(f"[QBO][CUSTOMER] Errore query fallback diretta: status {resp3.status_code} - {resp3.text}")
                        return None
                        
            except Exception as e2:
                logging.error(f"[QBO][CUSTOMER] Errore parsing errore duplicato customer: {e2}")
            logging.error(f"[QBO][CUSTOMER] Errore creazione cliente: {resp.status_code} {resp.text}")
            return None
    
    except Exception as e:
        logging.error(f"[QBO][CUSTOMER] Eccezione in trova_o_crea_customer: {e}")
        return None

def find_customer_with_robust_matching(customers_list, display_name):
    """
    Cerca un customer principale nella lista con strategie robuste di matching.
    
    Args:
        customers_list: Lista di customer da QuickBooks
        display_name: Nome da cercare
    
    Returns:
        dict: Customer trovato o None
    """
    import logging
    import re
    
    for c in customers_list:
        customer_display_name = c.get('DisplayName', '')
        
        # Skip sub-customers (hanno ParentRef)
        if c.get('ParentRef'):
            continue
        
        # Strategia 1: Match esatto
        if customer_display_name == display_name:
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match esatto), ID {c.get('Id')}")
            return c
        
        # Strategia 2: Match con trim (rimuove spazi iniziali/finali)
        if customer_display_name.strip() == display_name.strip():
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match trimmed), ID {c.get('Id')}")
            logging.info(f"[QBO][CUSTOMER] Input: '{display_name}' ({len(display_name)} chars) -> QB: '{customer_display_name}' ({len(customer_display_name)} chars)")
            return c
        
        # Strategia 3: Match normalizzato (rimuove caratteri invisibili)
        def normalize_string(s):
            import re
            # Rimuove caratteri invisibili e normalizza spazi
            return re.sub(r'\s+', ' ', s.strip())
        
        if normalize_string(customer_display_name) == normalize_string(display_name):
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match normalizzato), ID {c.get('Id')}")
            return c
        
        # Strategia 4: Match case-insensitive
        if customer_display_name.lower().strip() == display_name.lower().strip():
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match case-insensitive), ID {c.get('Id')}")
            return c
        
        # Strategia 5: Match con suffissi QuickBooks (es. "NOME (1234)")
        # Rimuove pattern come " (numero)" dal nome QB per confronto
        qb_name_clean = re.sub(r'\s*\(\d+\)\s*$', '', customer_display_name).strip()
        if qb_name_clean == display_name.strip():
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match con suffisso QB), ID {c.get('Id')}")
            logging.info(f"[QBO][CUSTOMER] QB name: '{customer_display_name}' -> Cleaned: '{qb_name_clean}' -> Input: '{display_name}'")
            return c
        
        # Strategia 6: Match case-insensitive con suffissi
        if qb_name_clean.lower() == display_name.lower().strip():
            logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match case-insensitive con suffisso), ID {c.get('Id')}")
            return c
        
        # Strategia 7: Match parziale (contiene il nome)
        if display_name.strip().lower() in customer_display_name.lower():
            # Verifica che non sia un match troppo generico
            if len(display_name.strip()) >= 5:  # Solo per nomi di almeno 5 caratteri
                logging.info(f"[QBO][CUSTOMER] Customer '{display_name}' trovato (match parziale), ID {c.get('Id')}")
                logging.info(f"[QBO][CUSTOMER] Input: '{display_name}' contained in QB: '{customer_display_name}'")
                return c
    
    return None

def find_subcustomer_with_robust_matching(customers_list, display_name, parent_id):
    """
    Cerca un sub-customer nella lista con strategie robuste di matching.
    
    Args:
        customers_list: Lista di customer da QuickBooks
        display_name: Nome da cercare
        parent_id: ID del parent customer
    
    Returns:
        dict: Customer trovato o None
    """
    import logging
    
    for c in customers_list:
        customer_display_name = c.get('DisplayName', '')
        customer_parent_ref = c.get('ParentRef', {}).get('value', '')
        
        # Strategia 1: Match esatto
        if customer_display_name == display_name and customer_parent_ref == parent_id:
            logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato (match esatto), ID {c.get('Id')}")
            return c
        
        # Strategia 2: Match con trim (rimuove spazi iniziali/finali) - RISOLVE CASO CSEXO25
        if customer_display_name.strip() == display_name.strip() and customer_parent_ref == parent_id:
            logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato (match trimmed), ID {c.get('Id')}")
            logging.info(f"[QBO][SUB-CUSTOMER] Input: '{display_name}' ({len(display_name)} chars) -> QB: '{customer_display_name}' ({len(customer_display_name)} chars)")
            return c
        
        # Strategia 3: Match normalizzato (rimuove caratteri invisibili)
        def normalize_string(s):
            import re
            # Rimuove caratteri invisibili e normalizza spazi
            return re.sub(r'\s+', ' ', s.strip())
        
        if normalize_string(customer_display_name) == normalize_string(display_name) and customer_parent_ref == parent_id:
            logging.info(f"[QBO][SUB-CUSTOMER] Sub-customer '{display_name}' trovato (match normalizzato), ID {c.get('Id')}")
            return c
    
    return None

def trova_o_crea_subcustomer(display_name, parent_id, subcustomer_data):
    """
    Trova un sub-cliente esistente in QuickBooks o ne crea uno nuovo
    (versione con strategie multiple per gestire apostrofi e spazi)
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
                
                # Usa la funzione di matching robusta
                found_customer = find_subcustomer_with_robust_matching(customers_all, display_name, parent_id)
                if found_customer:
                    return found_customer
                
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
                                
                                # Usa la funzione di matching robusta anche qui
                                found_customer = find_subcustomer_with_robust_matching(customers_all_fallback, display_name, parent_id)
                                if found_customer:
                                    return found_customer
                                
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
