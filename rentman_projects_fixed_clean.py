"""
🚀 MODULO CORRETTO PER PROGETTI RENTMAN
Usa la logica CORRETTA del rentman_api.py esistente:
- STATUS: usa in_financial=True per subprojects
- VALORI: usa primo subproject per order (NON financial)
"""

import requests
import config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
import os
import rentman_project_utils
from qb_customer import get_qb_import_status

# Configurazione logging
LOG_LEVEL = os.getenv('RENTMAN_LOG_LEVEL', 'INFO')
VERBOSE_MODE = LOG_LEVEL == 'DEBUG'

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')

def log_info(message):
    if VERBOSE_MODE:
        print(f"ℹ️ {message}")

def log_debug(message):
    if VERBOSE_MODE:
        print(f"🔍 {message}")

def log_warning(message):
    print(f"⚠️ {message}")

def log_error(message):
    print(f"❌ {message}")

# Cache globali
_projecttype_cache = {}
_status_cache = {}
_manager_cache = {}
_customer_cache = {}

# Lock thread-safe
_cache_lock = threading.Lock()
_manager_cache_lock = threading.Lock()
_customer_cache_lock = threading.Lock()


def get_projecttype_name_cached(type_id, headers):
    """Recupera il nome del tipo progetto con cache"""
    if not type_id:
        return ""
    
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
        log_error(f"Errore recuperando project type {type_id}: {e}")
    
    with _cache_lock:
        _projecttype_cache[type_id] = ""
    return ""


def extract_id_from_path(path):
    """Estrae l'ID da un path come '/projecttypes/123'"""
    if not path:
        return None
    try:
        return int(path.split('/')[-1])
    except (ValueError, IndexError):
        return None


def get_all_statuses(headers):
    """Recupera tutti gli status disponibili e crea una mappa ID->Nome"""
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
            log_error(f"Errore endpoint statuses: {response.status_code}")
    except Exception as e:
        log_error(f"Errore recuperando statuses: {e}")
    return {}


def get_project_subprojects_fast(project_ids, headers):
    """Recupera i subprojects - UGUALE AL RENTMAN_API.PY"""
    url = f"{config.REN_BASE_URL}/subprojects"
    
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


def get_project_status_fast(project_id, headers, status_map, main_project=None):
    """
    LOGICA STATUS CORRETTA dal rentman_api.py:
    - USA in_financial=True per gli STATUS
    """
    subprojects = get_project_subprojects_fast(project_id, headers)
    
    if subprojects:
        # 🎯 STATUS: Filtra solo subprojects con in_financial=True
        financial_subs = [s for s in subprojects if s.get('in_financial') is True]
        
        if financial_subs:
            # Seleziona quello con order più basso tra quelli finanziari
            subproject_principale = min(financial_subs, key=lambda s: s.get('order', 9999))
            status_path = subproject_principale.get('status')
            status_id = extract_id_from_path(status_path)
            value = subproject_principale.get('project_total_price')
            log_debug(f"[PROGETTO {project_id}] Subproject finanziario: status_id={status_id}, value={value}, order={subproject_principale.get('order')}")
            
            if status_id and status_id in status_map:
                return status_map[status_id]
        else:
            log_debug(f"[PROGETTO {project_id}] Nessun subproject con in_financial=True trovato")
    
    # Se nessun subproject valido, usa lo status del progetto principale
    if main_project:
        main_status_path = main_project.get('status')
        status_id = extract_id_from_path(main_status_path)
        value = main_project.get('project_total_price')
        log_debug(f"[PROGETTO {project_id}] Nessun subproject valido, status_id principale={status_id}, value principale={value}")
        
        if status_id and status_id in status_map:
            return status_map[status_id]
    
    return "Concept"


def get_customer_name_cached(customer_path, headers):
    """Recupera il nome del cliente con cache"""
    if not customer_path:
        return ""
    
    customer_id = extract_id_from_path(customer_path)
    if not customer_id:
        return ""
    
    with _customer_cache_lock:
        if customer_id in _customer_cache:
            return _customer_cache[customer_id]
    
    try:
        customer_url = f"{config.REN_BASE_URL}/contacts/{customer_id}"
        response = requests.get(customer_url, headers=headers, timeout=5)
        
        if response.ok:
            customer_data = response.json().get('data', {})
            customer_name = customer_data.get('displayname') or customer_data.get('name', '')
            
            with _customer_cache_lock:
                _customer_cache[customer_id] = customer_name
            
            log_debug(f"[CUSTOMER] Recuperato nome cliente {customer_id}: '{customer_name}'")
            return customer_name
        else:
            log_warning(f"[CUSTOMER] Errore HTTP {response.status_code} per cliente {customer_id}")
    except Exception as e:
        log_warning(f"[CUSTOMER] Errore recuperando cliente {customer_id}: {e}")
    
    with _customer_cache_lock:
        _customer_cache[customer_id] = ""
    return ""


def preload_customers_batch(customer_paths, headers):
    """Precarica i nomi dei clienti in batch"""
    if not customer_paths:
        return {}
    
    customer_ids = []
    for path in customer_paths:
        if path:
            customer_id = extract_id_from_path(path)
            if customer_id:
                customer_ids.append(customer_id)
    
    if not customer_ids:
        return {}
    
    missing_ids = []
    result = {}
    
    with _customer_cache_lock:
        for customer_id in customer_ids:
            if customer_id in _customer_cache:
                result[customer_id] = _customer_cache[customer_id]
            else:
                missing_ids.append(customer_id)
    
    log_debug(f"[CUSTOMER BATCH] Cache hit: {len(result)}, Missing: {len(missing_ids)}")
    
    if not missing_ids:
        return result
    
    def fetch_customer(customer_id):
        try:
            customer_url = f"{config.REN_BASE_URL}/contacts/{customer_id}"
            response = requests.get(customer_url, headers=headers, timeout=5)
            
            if response.ok:
                customer_data = response.json().get('data', {})
                customer_name = customer_data.get('displayname') or customer_data.get('name', '')
                return customer_id, customer_name
            else:
                return customer_id, ""
        except Exception:
            return customer_id, ""
    
    try:
        with ThreadPoolExecutor(max_workers=min(10, len(missing_ids))) as executor:
            futures = [executor.submit(fetch_customer, customer_id) for customer_id in missing_ids]
            
            batch_results = {}
            for future in futures:
                customer_id, customer_name = future.result()
                batch_results[customer_id] = customer_name
                result[customer_id] = customer_name
            
            with _customer_cache_lock:
                _customer_cache.update(batch_results)
            
            log_info(f"[CUSTOMER BATCH] Precaricati {len(batch_results)} nomi clienti")
            
    except Exception as e:
        log_error(f"[CUSTOMER BATCH] Errore durante batch loading: {e}")
    
    return result


def process_project(project_data, headers, status_map, start_dt, end_dt, debug_count):
    """
    LOGICA CORRETTA dal rentman_api.py:
    - STATUS: usa in_financial=True
    - VALORI: usa primo subproject per order, se None somma tutti i subprojects, se ancora None usa project_total_price
    - INCLUDI TUTTI GLI STATUS (nessun filtro)
    - Se project_total_price è None, somma i valori dei subprojects
    - FILTRO PERIODO: includi se c'è sovrapposizione tra [period_start, period_end] e [start_dt, end_dt]
    """
    try:
        p = project_data
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        project_id = p.get('id')
        project_name = p.get('name', '')
        log_debug(f"[PROCESS] Progetto {project_id} - '{project_name}' | period_start: {period_start} | period_end: {period_end}")

        # Filtro periodo: includi se almeno un giorno nel range
        if not period_start or not period_end:
            log_debug(f"[PERIODO] ❌ ESCLUSO - Progetto {project_id} ('{project_name}') senza period_start o period_end")
            return None
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
            # INCLUSIVO: includi se c'è sovrapposizione tra periodi
            if pe < start_dt or ps > end_dt:
                log_debug(f"[PERIODO] ❌ ESCLUSO - Progetto {project_id} ('{project_name}') periodo {period_start[:10]} → {period_end[:10]} FUORI da range {start_dt} → {end_dt}")
                return None
        except Exception as e:
            log_debug(f"[PROGETTO {project_id}] Errore parsing periodo: {e}")
            return None

        project_type_path = p.get('project_type')
        project_type_id = extract_id_from_path(project_type_path)

        # STATUS: usa la logica con in_financial=True (ma non filtra più per status)
        project_status = get_project_status_fast(project_id, headers, status_map, main_project=p)

        raw_number = p.get("number")
        converted_number = str(raw_number) if raw_number is not None else "N/A"

        # LOGICA VALORE: usa primo subproject per order, se None somma tutti i subprojects, se ancora None usa project_total_price
        project_value = None
        subprojects = get_project_subprojects_fast(project_id, headers)
        if subprojects:
            subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
            val = subproject_principale.get('project_total_price')
            try:
                if val is not None:
                    project_value = float(val)
            except Exception:
                pass
            if (project_value is None or project_value == 0.0):
                # Somma tutti i valori dei subprojects se il principale è None o 0
                somma = 0.0
                almeno_uno = False
                for sub in subprojects:
                    val = sub.get('project_total_price')
                    try:
                        if val is not None:
                            somma += float(val)
                            almeno_uno = True
                    except Exception:
                        pass
                if almeno_uno and somma > 0:
                    project_value = somma
        if project_value is None or project_value == 0.0:
            val = p.get('project_total_price')
            try:
                if val is not None:
                    project_value = float(val)
            except Exception:
                pass
        if project_value is None:
            project_value = 0.0

        # Recupero dati responsabile progetto
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
                                    log_warning(f"[WARN] Responsabile NON valorizzato per progetto {project_id} (manager_id={manager_id})")
                            else:
                                log_warning(f"[WARN] Errore HTTP recuperando responsabile progetto {project_id} (manager_id={manager_id}): {crew_resp.status_code}")
                        except Exception as e:
                            log_warning(f"[WARN] Errore recuperando responsabile progetto {manager_id}: {e}")

        # Recupero nome cliente
        customer_name = ""
        customer_path = p.get('customer')
        if customer_path:
            customer_name = get_customer_name_cached(customer_path, headers)
            log_debug(f"[PROGETTO {project_id}] Nome cliente: '{customer_name}'")

        project_type_name = get_projecttype_name_cached(project_type_id, headers) if project_type_id else ""

        return {
            "id": project_id,
            "number": converted_number,
            "name": p.get("name") or "",
            "status": project_status,
            "equipment_period_from": period_start[:10] if period_start else None,
            "equipment_period_to": period_end[:10] if period_end else None,
            "project_type_id": project_type_id,
            "project_type_name": project_type_name,
            "project_value": project_value,
            "project_total_price": project_value,
            "manager_name": manager_name,
            "manager_email": manager_email,
            "contact_displayname": customer_name,
            "cliente": customer_name,
            "QB_IMPORT": ""
        }
    except Exception as e:
        log_error(f"Errore processando progetto {p.get('id', 'unknown')}: {e}")
        return None


def list_projects_by_date_unified(from_date, to_date, mode="normal"):
    """FUNZIONE UNIFICATA per recuperare progetti per data"""
    log_info(f"🚀 Avvio recupero progetti unificato (modalità: {mode})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti
    url = f"{config.REN_BASE_URL}/projects"
    log_debug(f"🔄 Recupero progetti con chiamata standard...")
    
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    
    projects = response.json().get('data', [])
    log_debug(f"📄 Progetti recuperati: {len(projects)}")
    
    # Filtro date
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    log_debug(f"⏳ Filtraggio progetti per periodo {from_date} - {to_date}...")
    
    # Precarica nomi clienti in batch
    log_debug("👥 Precaricamento nomi clienti in batch...")
    customer_paths = [p.get('customer') for p in projects if p.get('customer')]
    if customer_paths:
        preload_customers_batch(customer_paths, headers)
        log_debug(f"✅ Precaricati {len(customer_paths)} nomi clienti in batch")
    
    # Processa progetti
    filtered = []
    debug_count = [0]
    
    for p in projects:
        result = process_project(p, headers, status_map, start_dt, end_dt, debug_count)
        if result:
            filtered.append(result)
    
    log_debug(f"✅ Progetti filtrati: {len(filtered)}")
    
    # Recupera project type names in parallelo
    if filtered:
        log_debug("🏷️ Recupero nomi project types...")
        unique_type_ids = set(p['project_type_id'] for p in filtered if p['project_type_id'])
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            type_name_futures = {
                type_id: executor.submit(get_projecttype_name_cached, type_id, headers)
                for type_id in unique_type_ids
            }
            
            for project in filtered:
                type_id = project['project_type_id']
                if type_id and type_id in type_name_futures:
                    try:
                        project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                    except:
                        project['project_type_name'] = ""
    
    log_info(f"🎉 Completato! Restituiti {len(filtered)} progetti con nomi clienti")
    return filtered


def list_projects_by_date_paginated_unified(from_date, to_date, page_size=20):
    """Generator che yield pagine di progetti processati"""
    log_info(f"🚀 Avvio recupero progetti paginato unificato (pagine da {page_size})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti base
    url = f"{config.REN_BASE_URL}/projects"
    log_debug(f"🔄 Recupero progetti con chiamata standard...")
    
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    
    projects = response.json().get('data', [])
    log_debug(f"📄 Progetti recuperati: {len(projects)}")
    
    # Pre-filtra progetti per date
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    date_filtered_projects = []
    for p in projects:
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        
        if not period_start or not period_end:
            continue
            
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
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
        
        # Precarica nomi clienti per questa pagina
        page_customer_paths = [p.get('customer') for p in page_projects if p.get('customer')]
        if page_customer_paths:
            preload_customers_batch(page_customer_paths, headers)
            log_debug(f"👥 Precaricati {len(page_customer_paths)} nomi clienti per pagina {page_num}")
        
        page_results = []
        for p in page_projects:
            result = process_project(p, headers, status_map, start_dt, end_dt, debug_count)
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


def list_projects_by_date_paginated_full_unified(from_date, to_date, page_size=20):
    """
    Versione allineata allo script standalone: usa funzioni condivise per filtro data, stato e dettagli.
    """
    import config
    import requests
    STATI_INTERESSE = ["In location", "Rientrato", "Confermato", "Pronto"]
    base_url = getattr(config, 'REN_BASE_URL', 'https://api.rentman.net')
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    # 1. Scarica tutti i progetti grezzi con paginazione
    url = f"{base_url}/projects"
    params = {
        'sort': '+id',
        'id[gt]': 2900,  # Ripristinato filtro id
        'fields': 'id,name,number,planperiod_start,planperiod_end',
        'limit': page_size,
        'offset': 0
    }
    all_projects = []
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if not resp.ok:
            break
        page_projects = resp.json().get('data', [])
        all_projects.extend(page_projects)
        if len(page_projects) < params['limit']:
            break
        params['offset'] += params['limit']
    print(f"DEBUG: Progetti grezzi scaricati: {len(all_projects)}")
    if not all_projects:
        print("ATTENZIONE: Nessun progetto trovato dalla API Rentman per il periodo richiesto (controlla parametri, connessione, filtro id[gt]=2900, ecc.)")
    # 2. Filtro locale per data (usa solo from_date, come nello script)
    filtered_projects = rentman_project_utils.filter_projects_by_date(all_projects, from_date, to_date)
    # 3. Filtro per stato e recupero dettagli
    detailed_projects = []
    filtered = rentman_project_utils.filter_projects_by_status(filtered_projects, headers, STATI_INTERESSE, base_url)
    for p, status_name in filtered:
        project_id = p.get('id')
        # Recupera dettagli progetto (cliente, responsabile, tipo, valore, email)
        project_url = f"{base_url}/projects/{project_id}"
        resp = requests.get(project_url, headers=headers, timeout=10)
        if not resp.ok:
            continue
        data = resp.json().get('data', {})
        # Cliente
        customer_name = ""
        customer_path = data.get('customer')
        if customer_path:
            customer_id = rentman_project_utils.extract_id_from_path(customer_path)
            if customer_id:
                customer_url = f"{base_url}/contacts/{customer_id}"
                cust_resp = requests.get(customer_url, headers=headers, timeout=10)
                if cust_resp.ok:
                    cust_data = cust_resp.json().get('data', {})
                    customer_name = cust_data.get('displayname') or cust_data.get('name', '')
        # Responsabile
        manager_name = None
        manager_email = None
        account_manager_path = data.get('account_manager')
        if account_manager_path:
            manager_id = rentman_project_utils.extract_id_from_path(account_manager_path)
            if manager_id:
                crew_url = f"{base_url}/crew/{manager_id}"
                crew_resp = requests.get(crew_url, headers=headers, timeout=10)
                if crew_resp.ok:
                    crew_data = crew_resp.json().get('data', {})
                    manager_name = crew_data.get('name') or crew_data.get('displayname')
                    manager_email = crew_data.get('email') or crew_data.get('email_1')
        # Tipo progetto
        project_type_name = ""
        project_type_path = data.get('project_type')
        if project_type_path:
            project_type_id = rentman_project_utils.extract_id_from_path(project_type_path)
            if project_type_id:
                type_url = f"{base_url}/projecttypes/{project_type_id}"
                type_resp = requests.get(type_url, headers=headers, timeout=10)
                if type_resp.ok:
                    type_data = type_resp.json().get('data', {})
                    project_type_name = type_data.get('name', '')
        # Valore progetto
        valore = data.get('project_total_price')
        try:
            valore = round(float(valore), 2) if valore is not None else None
        except Exception:
            valore = None
        # QB Import status
        qb_import = get_qb_import_status(project_id)
        detailed_projects.append({
            'id': project_id,
            'name': p.get('name', ''),
            'number': p.get('number', ''),
            'status': status_name,
            'project_total_price': valore,
            'equipment_period_from': p.get('planperiod_start', '')[:10] if p.get('planperiod_start') else '',
            'equipment_period_to': p.get('planperiod_end', '')[:10] if p.get('planperiod_end') else '',
            'contact_displayname': customer_name,
            'manager_name': manager_name,
            'manager_email': manager_email,
            'project_type_name': project_type_name,
            'qb_import': qb_import
        })
    print("\n--- LISTA PROGETTI DOPO FILTRO STATO ---")
    for p, status_name in filtered:
        print(f"ID: {p.get('id')} | Numero: {p.get('number')} | Nome: {p.get('name')} | Stato: {status_name}")
    print(f"Totale progetti DOPO filtro stato: {len(filtered)}\n")
    return detailed_projects


def clear_cache():
    """Svuota tutte le cache"""
    global _projecttype_cache, _status_cache, _manager_cache, _customer_cache
    
    with _cache_lock:
        _projecttype_cache.clear()
        _status_cache.clear()
    
    with _manager_cache_lock:
        _manager_cache.clear()
    
    with _customer_cache_lock:
        _customer_cache.clear()
    
    log_info("🧹 Tutte le cache unificate svuotate")


def list_projects_id_gt_2900_paged(fields=None, page_size=100, debug_print=True):
    """
    Recupera TUTTI i progetti con id > 2900 usando paginazione Rentman API.
    Stampa tutti i campi richiesti per ogni progetto in modo semplice e leggibile (no tabella).
    """
    import time
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/projects"
    offset = 0
    limit = page_size
    all_projects = []
    page = 1
    params_base = {
        'limit': limit,
        'offset': offset,
        'sort': '+id',
        'id[gt]': 2900
    }
    if fields:
        params_base['fields'] = fields
    while True:
        params = params_base.copy()
        params['offset'] = offset
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if not response.ok:
            log_error(f"Errore Rentman API: {response.status_code} {response.text}")
            break
        page_projects = response.json().get('data', [])
        if not page_projects:
            break
        all_projects.extend(page_projects)
        if debug_print:
            print(f"\n--- Pagina {page} (offset={offset}) ---")
            for p in page_projects:
                print(f"ID: {p.get('id','')} | Numero: {p.get('number','')} | Nome: {p.get('name','')}")
                print(f"  Status: {p.get('status','')} | Valore: {p.get('project_total_price','')}")
                print(f"  Periodo: {p.get('planperiod_starin_financialt','')} → {p.get('planperiod_end','')}")
                print(f"  Cliente: {p.get('customer','')} | Tipo: {p.get('project_type','')} | Resp.: {p.get('account_manager','')}")
                print("-")
        if len(page_projects) < limit:
            break
        offset += limit
        page += 1
        time.sleep(0.2)  # Rispetta rate limit
    print(f"\nTotale progetti trovati con id>2900: {len(all_projects)}")
    # Stampa solo i primi 10 e gli ultimi 10 progetti
    n = 10
    total = len(all_projects)
    if total <= n * 2:
        to_show = all_projects
    else:
        to_show = all_projects[:n] + all_projects[-n:]
    print(f"\n--- Visualizzazione primi {min(n, total)} e ultimi {min(n, total)} progetti ---")
    for idx, p in enumerate(to_show):
        print(f"ID: {p.get('id','')} | Numero: {p.get('number','')} | Nome: {p.get('name','')}")
        print(f"  Status: {p.get('status','')} | Valore: {p.get('project_total_price','')}")
        print(f"  Periodo: {p.get('planperiod_start','')} → {p.get('planperiod_end','')}")
        print(f"  Cliente: {p.get('customer','')} | Tipo: {p.get('project_type','')} | Resp.: {p.get('account_manager','')}")
        print("-")
        if total > n * 2 and idx == n - 1:
            print("... ... ... (omessi progetti intermedi) ... ... ...\n")
    return all_projects


# Alias per compatibilità
list_projects_by_date = list_projects_by_date_unified
list_projects_by_date_paginated_full = list_projects_by_date_paginated_full_unified

def filter_projects_by_status(projects, stati_interesse):
    """
    Filtra i progetti in base a una lista di stati di interesse (case-insensitive).
    Esempio: stati_interesse = ["Confirmed", "In progress", "Completed"]
    """
    stati_set = set(s.lower() for s in stati_interesse)
    return [p for p in projects if p.get('status', '').lower() in stati_set]

# ESEMPIO DI UTILIZZO:
# Supponiamo di aver già ottenuto la lista dei progetti filtrati per data:
# progetti_filtrati = list_projects_by_date('2025-06-06', '2025-06-06')
# Stati di interesse:
# stati_interesse = ["In location", "Rientrato", "Confermato", "Pronto"]
# progetti_finali = filter_projects_by_status(progetti_filtrati, stati_interesse)
# print(f"Progetti con stati di interesse: {len(progetti_finali)}")
# for p in progetti_finali:
#     print(f"ID: {p['id']} | Stato: {p['status']} | Valore: {p['project_value']:.2f}")
#
# Se vuoi vedere tutti gli stati presenti nei progetti filtrati:
# stati_presenti = set(p['status'] for p in progetti_filtrati)
# print(sorted(stati_presenti))

def list_projects_by_number_full_unified(project_number):
    """
    Ricerca e restituisce i dettagli di un progetto (o più progetti) dato il numero progetto,
    usando la stessa logica di dettaglio/stato della ricerca per data.
    """
    import config
    STATI_INTERESSE = ["In location", "Rientrato", "Confermato", "Pronto"]
    base_url = getattr(config, 'REN_BASE_URL', 'https://api.rentman.net')
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    # Ricerca progetto per numero
    url = f"{base_url}/projects"
    params = {
        'number': project_number,
        'fields': 'id,name,number,planperiod_start,planperiod_end',
        'limit': 10,
        'offset': 0
    }
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if not resp.ok:
        return []
    projects = resp.json().get('data', [])
    # Filtro per stato e recupero dettagli (come per data)
    detailed_projects = []
    filtered = rentman_project_utils.filter_projects_by_status(projects, headers, STATI_INTERESSE, base_url)
    for p, status_name in filtered:
        project_id = p.get('id')
        # Recupera dettagli progetto (cliente, responsabile, tipo, valore, email)
        project_url = f"{base_url}/projects/{project_id}"
        resp = requests.get(project_url, headers=headers, timeout=10)
        if not resp.ok:
            continue
        data = resp.json().get('data', {})
        # Cliente
        customer_name = ""
        customer_path = data.get('customer')
        if customer_path:
            customer_id = rentman_project_utils.extract_id_from_path(customer_path)
            if customer_id:
                customer_url = f"{base_url}/contacts/{customer_id}"
                cust_resp = requests.get(customer_url, headers=headers, timeout=10)
                if cust_resp.ok:
                    cust_data = cust_resp.json().get('data', {})
                    customer_name = cust_data.get('displayname') or cust_data.get('name', '')
        # Responsabile
        manager_name = None
        manager_email = None
        account_manager_path = data.get('account_manager')
        if account_manager_path:
            manager_id = rentman_project_utils.extract_id_from_path(account_manager_path)
            if manager_id:
                crew_url = f"{base_url}/crew/{manager_id}"
                crew_resp = requests.get(crew_url, headers=headers, timeout=10)
                if crew_resp.ok:
                    crew_data = crew_resp.json().get('data', {})
                    manager_name = crew_data.get('name') or crew_data.get('displayname')
                    manager_email = crew_data.get('email') or crew_data.get('email_1')
        # Tipo progetto
        project_type_name = ""
        project_type_path = data.get('project_type')
        if project_type_path:
            project_type_id = rentman_project_utils.extract_id_from_path(project_type_path)
            if project_type_id:
                type_url = f"{base_url}/projecttypes/{project_type_id}"
                type_resp = requests.get(type_url, headers=headers, timeout=10)
                if type_resp.ok:
                    type_data = type_resp.json().get('data', {})
                    project_type_name = type_data.get('name', '')
        # Valore progetto
        valore = data.get('project_total_price')
        try:
            valore = round(float(valore), 2) if valore is not None else None
        except Exception:
            valore = None
        # QB Import status
        qb_import = get_qb_import_status(project_id)
        detailed_projects.append({
            'id': project_id,
            'name': p.get('name', ''),
            'number': p.get('number', ''),
            'status': status_name,
            'project_total_price': valore,
            'equipment_period_from': p.get('planperiod_start', '')[:10] if p.get('planperiod_start') else '',
            'equipment_period_to': p.get('planperiod_end', '')[:10] if p.get('planperiod_end') else '',
            'contact_displayname': customer_name,
            'manager_name': manager_name,
            'manager_email': manager_email,
            'project_type_name': project_type_name,
            'qb_import': qb_import
        })
    return detailed_projects