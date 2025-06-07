import requests
import config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')

# Cache globali per ottimizzazione
_projecttype_cache = {}
_status_cache = {}
_cache_lock = threading.Lock()

# Cache thread-safe per responsabili
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
        logging.info(f"[SUBPROJECTS] GET {url} params={params} status={response.status_code}")
        if response.ok:
            data = response.json().get('data', [])
            if isinstance(data, dict):
                data = [data]
            logging.info(f"[SUBPROJECTS] Trovati {len(data)} subprojects per {len(project_ids)} progetti")
            for sub in data:
                pid = sub.get('project')
                status = sub.get('status')
                order = sub.get('order')
                sub_id = sub.get('id')
                # Il valore del subproject è project_total_price, non quello del progetto principale
                value = sub.get('project_total_price')
                logging.info(f"  - Subproject ID {sub_id} (project {pid}, order {order}): status={status}, value={value}")
            return data
        elif response.status_code == 404:
            logging.warning(f"[SUBPROJECTS] Nessun subproject trovato per {project_ids}")
            return []
        else:
            logging.error(f"[SUBPROJECTS] Errore HTTP {response.status_code} per {project_ids}")
            return []
    except Exception as e:
        logging.error(f"[SUBPROJECTS] Exception: {e}")
        return []

def get_project_status_fast(project_id, headers, status_map, main_project=None):
    """ Recupera lo status del progetto: preferisce il subproject con order più basso, altrimenti quello principale """
    subprojects = get_project_subprojects_fast(project_id, headers)
    # Se ci sono subprojects, cerca quello con order più basso con uno status valido
    if subprojects:
        subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
        status_path = subproject_principale.get('status')
        status_id = extract_id_from_path(status_path)
        value = subproject_principale.get('project_total_price')
        logging.info(f"[PROGETTO {project_id}] Subproject principale: status_id={status_id}, value={value}")
        if status_id and status_id in status_map:
            return status_map[status_id]
    # Se nessun subproject valido, prova a usare lo status del progetto principale
    if main_project:
        main_status_path = main_project.get('status')
        status_id = extract_id_from_path(main_status_path)
        value = main_project.get('project_total_price')
        logging.info(f"[PROGETTO {project_id}] Nessun subproject valido, status_id principale={status_id}, value principale={value}")
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
        project_id = p.get('id')
        project_status = get_project_status_fast(project_id, headers, status_map, main_project=p)
        raw_number = p.get("number")
        converted_number = str(raw_number) if raw_number is not None else "N/A"
        # Estrazione robusta del valore
        project_value = None
        subprojects = get_project_subprojects_fast(project_id, headers)
        if subprojects:
            subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
            project_value = subproject_principale.get('project_total_price')
            logging.info(f"[PROGETTO {project_id}] Valore dal subproject principale: {project_value}")
        if project_value is None or str(project_value).strip() == '':
            project_value = p.get('project_total_price')
            logging.info(f"[PROGETTO {project_id}] Valore dal progetto principale: {project_value}")
        try:
            formatted_value = '{:.2f}'.format(float(project_value))
        except (ValueError, TypeError):
            formatted_value = '0.00'
        # --- Recupero dati responsabile progetto ---
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
                                    logging.warning(f"[WARN] Responsabile NON valorizzato per progetto {project_id} (manager_id={manager_id}) - crew_data: {crew_data}")
                            else:
                                logging.warning(f"[WARN] Errore HTTP recuperando responsabile progetto {project_id} (manager_id={manager_id}): {crew_resp.status_code} - {crew_resp.text}")
                        except Exception as e:
                            logging.warning(f"[WARN] Errore recuperando responsabile progetto {manager_id}: {e}")
            else:
                logging.warning(f"[WARN] account_manager_path presente ma manager_id non estratto per progetto {project_id} (path: {account_manager_path})")
        else:
            logging.warning(f"[WARN] Nessun account_manager per progetto {project_id}")
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
            "project_value": formatted_value,
            "manager_name": manager_name,
            "manager_email": manager_email
        }
    except Exception as e:
        logging.error(f"Errore processando progetto {p.get('id', 'unknown')}: {e}")
        return None

def list_projects_by_date(from_date, to_date):
    """Versione aggiornata: usa la logica robusta di debug_lista_progetti2.py per estrarre la lista progetti, status e valore coerenti con la fast API v2"""
    from rentman_api_fast_v2 import RentmanFastAPI
    import config
    api = RentmanFastAPI(config.REN_API_TOKEN)
    # Recupera progetti ottimizzati (già filtra per periodo e ID >= 2900)
    progetti = api.list_projects_by_date_optimized(from_date, to_date)
    # Adatta output per compatibilità (se serve)
    print(f"[INFO] Completato! Restituiti {len(progetti)} progetti (via fast_v2)")
    return progetti

# Funzione per svuotare le cache se necessario
def clear_cache():
    """ Svuota le cache per forzare il refresh """
    global _projecttype_cache, _status_cache
    with _cache_lock:
        _projecttype_cache.clear()
        _status_cache.clear()
    print("🧹 Cache svuotata")

def get_project_and_customer(project_id):
    """
    Recupera i dettagli di un progetto specifico e del cliente associato
    
    Args:
        project_id: L'ID del progetto da recuperare
        
    Returns:
        dict: Un dizionario contenente le chiavi 'project' e 'customer'
    """
    print(f"📊 Recupero progetto {project_id} e cliente associato...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera il progetto
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if not response.ok:
            raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
        
        project = response.json().get('data', {})
        if not project:
            raise Exception(f"Progetto {project_id} non trovato")
        
        # Recupera il cliente associato al progetto
        customer_path = project.get('customer')
        if not customer_path:
            raise Exception(f"Progetto {project_id} non ha un cliente associato")
            
        customer_id = extract_id_from_path(customer_path)
        if not customer_id:
            raise Exception(f"ID cliente non valido: {customer_path}")
        
        # Recupera i dati del cliente
        customer_url = f"{config.REN_BASE_URL}/contacts/{customer_id}"
        customer_response = requests.get(customer_url, headers=headers)
        
        if not customer_response.ok:
            raise Exception(f"Errore recuperando cliente {customer_id}: {customer_response.status_code}")
            
        customer = customer_response.json().get('data', {})
        if not customer:
            raise Exception(f"Cliente {customer_id} non trovato")
        
        print(f"✅ Recuperati dati di progetto {project_id} e cliente {customer_id}")
        
        return {
            "project": project,
            "customer": customer
        }
        
    except Exception as e:
        print(f"❌ Errore recuperando progetto {project_id}: {e}")
        raise