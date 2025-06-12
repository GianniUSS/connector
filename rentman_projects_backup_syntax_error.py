"""
🚀 MODULO UNIFICATO PER PROGETTI RENTMAN - VERSIONE OTTIMIZZATA
Elimina duplicazioni di codice tra rentman_api.py e qb_customer.py
Include funzionalità per recuperare nomi clienti per risolvere il problema nella griglia
INCLUDE: preload_customers_batch() per ottimizzazioni performance
"""

import requests
import config
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import logging
import os
import time  # 🚀 NUOVO: Per sleep e timing
import random  # 🚀 NUOVO: Per gestione rate limiting

# Configurazione logging
LOG_LEVEL = os.getenv('RENTMAN_LOG_LEVEL', 'INFO')
VERBOSE_MODE = LOG_LEVEL == 'DEBUG'

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s')

def log_info(message):
    """Log controllabile per messaggi informativi - OTTIMIZZATO per performance"""
    # OTTIMIZZAZIONE: Solo log critici in produzione
    if VERBOSE_MODE:
        print(f"ℹ️ {message}")

def log_debug(message):
    """Log controllabile per messaggi di debug - OTTIMIZZATO per performance"""
    # OTTIMIZZAZIONE: Solo in modalità debug
    if VERBOSE_MODE:
        print(f"🔍 {message}")

def log_warning(message):
    """Log sempre visibile per warning"""
    print(f"⚠️ {message}")

def log_error(message):
    """Log sempre visibile per errori"""
    print(f"❌ {message}")

# Cache globali per ottimizzazione
_projecttype_cache = {}
_status_cache = {}
_manager_cache = {}
_customer_cache = {}  # 🚀 NUOVO: Cache per nomi clienti
customer_name_cache = {}  # 🚀 NUOVO: Cache globale per batch loading clienti

# Lock thread-safe per le cache
_cache_lock = threading.Lock()
_manager_cache_lock = threading.Lock()
_customer_cache_lock = threading.Lock()  # 🚀 NUOVO: Lock per cache clienti

# 🚀 NUOVO: Cache per valori singoli progetti
_project_value_cache = {}
_project_value_cache_lock = threading.Lock()


def get_single_project_value(project_id, headers):
    """
    🎯 RECUPERA IL VALORE DA UN SINGOLO PROGETTO
    Soluzione per il problema project_total_price=None nella collezione
    
    Args:
        project_id: ID del progetto
        headers: Headers per API Rentman
        
    Returns:
        float: Valore del progetto o None se non trovato
    """
    # Controlla cache prima
    with _project_value_cache_lock:
        if project_id in _project_value_cache:
            cached_value = _project_value_cache[project_id]
            log_debug(f"[VALORE CACHE] Progetto {project_id}: {cached_value}")
            return cached_value
    
    # Recupera progetto singolo dall'API
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    
    try:
        log_debug(f"[VALORE API] Recuperando progetto singolo {project_id}...")
        response = requests.get(url, headers=headers, timeout=8)
        
        if response.ok:
            project_data = response.json().get('data', {})
            project_total_price = project_data.get('project_total_price')
            
            # Cache del risultato (anche se None)
            with _project_value_cache_lock:
                _project_value_cache[project_id] = project_total_price
            
            log_debug(f"[VALORE API] Progetto {project_id}: project_total_price = {project_total_price}")
            return project_total_price
        else:
            log_warning(f"[VALORE API] Errore HTTP {response.status_code} per progetto {project_id}")
            return None
            
    except Exception as e:
        log_error(f"[VALORE API] Errore recuperando progetto {project_id}: {e}")
        return None


def get_multiple_project_values_batch(project_ids, headers):
    """
    🚀 RECUPERA I VALORI DI MULTIPLI PROGETTI IN BATCH
    Ottimizzazione per evitare troppe chiamate API singole
    
    Args:
        project_ids: Lista di ID dei progetti
        headers: Headers per API Rentman
        
    Returns:
        dict: Mappa project_id -> project_total_price
    """
    if not project_ids:
        return {}
    
    log_debug(f"[BATCH VALUES] Recuperando valori per {len(project_ids)} progetti...")
    
    # Filtra solo progetti non in cache
    uncached_ids = []
    results = {}
    
    with _project_value_cache_lock:
        for pid in project_ids:
            if pid in _project_value_cache:
                results[pid] = _project_value_cache[pid]
                log_debug(f"[BATCH CACHE] Progetto {pid}: {_project_value_cache[pid]}")
            else:
                uncached_ids.append(pid)
    
    if not uncached_ids:
        log_debug(f"[BATCH VALUES] Tutti i valori già in cache!")
        return results
    
    log_debug(f"[BATCH VALUES] Recuperando {len(uncached_ids)} progetti non in cache...")
    
    # Recupera in batch usando ThreadPoolExecutor
    def fetch_single_value(project_id):
        url = f"{config.REN_BASE_URL}/projects/{project_id}"
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.ok:
                project_data = response.json().get('data', {})
                value = project_data.get('project_total_price')
                return project_id, value
            else:
                log_warning(f"[BATCH] Errore HTTP {response.status_code} per progetto {project_id}")
                return project_id, None
        except Exception as e:
            log_error(f"[BATCH] Errore progetto {project_id}: {e}")
            return project_id, None
    
    # Batch processing con max 8 worker per evitare rate limiting
    from concurrent.futures import ThreadPoolExecutor, as_completed
    batch_results = {}
    
    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit tutti i jobs
        futures = {executor.submit(fetch_single_value, pid): pid for pid in uncached_ids}
        
        # Raccogli risultati
        completed = 0
        for future in as_completed(futures):
            project_id, value = future.result()
            batch_results[project_id] = value
            results[project_id] = value
            completed += 1
            
            if completed % 10 == 0:
                log_debug(f"[BATCH PROGRESS] {completed}/{len(uncached_ids)} completati")
    
    # Aggiorna cache
    with _project_value_cache_lock:
        for pid, value in batch_results.items():
            _project_value_cache[pid] = value
    
    log_debug(f"[BATCH VALUES] Completato! {len(batch_results)} nuovi valori recuperati")
    return results


def get_batch_project_values(project_ids, headers):
    """
    🚀 RECUPERO BATCH DEI VALORI DA PROGETTI SINGOLI
    Ottimizzazione per recuperare più valori contemporaneamente
    
    Args:
        project_ids: Lista di ID progetti
        headers: Headers per API Rentman
        
    Returns:
        dict: Mappa project_id -> valore
    """
    if not project_ids:
        return {}
    
    log_debug(f"[BATCH VALUES] Recuperando valori per {len(project_ids)} progetti...")
    
    # Filtra progetti non ancora in cache
    uncached_ids = []
    cached_values = {}
    
    with _project_value_cache_lock:
        for project_id in project_ids:
            if project_id in _project_value_cache:
                cached_values[project_id] = _project_value_cache[project_id]
            else:
                uncached_ids.append(project_id)
    
    if cached_values:
        log_debug(f"[BATCH VALUES] {len(cached_values)} valori trovati in cache")
    
    if not uncached_ids:
        log_debug(f"[BATCH VALUES] Tutti i valori erano già in cache")
        return cached_values
    
    log_debug(f"[BATCH VALUES] Recuperando {len(uncached_ids)} valori dall'API...")
    
    def fetch_single_value(project_id):
        """Recupera valore singolo per thread pool"""
        try:
            url = f"{config.REN_BASE_URL}/projects/{project_id}"
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.ok:
                project_data = response.json().get('data', {})
                value = project_data.get('project_total_price')
                return project_id, value
            else:
                log_warning(f"[BATCH] Errore {response.status_code} per progetto {project_id}")
                return project_id, None
                
        except Exception as e:
            log_warning(f"[BATCH] Errore progetto {project_id}: {e}")
            return project_id, None
    
    # Esegui in batch con ThreadPoolExecutor
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    batch_values = {}
    start_time = time.time()
    
    # Usa max 5 worker per evitare rate limiting
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Suddividi in batch più piccoli
        batch_size = 10
        for i in range(0, len(uncached_ids), batch_size):
            batch = uncached_ids[i:i + batch_size]
            
            # Aggiungi delay tra batch
            if i > 0:
                time.sleep(0.3)
            
            futures = {executor.submit(fetch_single_value, pid): pid for pid in batch}
            
            for future in as_completed(futures):
                project_id, value = future.result()
                batch_values[project_id] = value
    
    # Cache tutti i risultati
    with _project_value_cache_lock:
        _project_value_cache.update(batch_values)
    
    elapsed = time.time() - start_time
    log_debug(f"[BATCH VALUES] Completato in {elapsed:.2f}s: {len(batch_values)} nuovi valori")
    
    # Combina cache e batch
    all_values = {**cached_values, **batch_values}
    return all_values


def get_multiple_project_values_batch(project_ids, headers, max_workers=3):
    """
    🚀 OTTIMIZZAZIONE: Recupera valori di multipli progetti in batch
    
    Args:
        project_ids: Lista di ID progetti
        headers: Headers per API Rentman  
        max_workers: Numero massimo di thread (default: 3 per evitare rate limiting)
        
    Returns:
        dict: Mappa project_id -> valore
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time
    
    if not project_ids:
        return {}
    
    result_values = {}
    projects_to_fetch = []
    
    # Controlla cache prima
    with _project_value_cache_lock:
        for pid in project_ids:
            if pid in _project_value_cache:
                result_values[pid] = _project_value_cache[pid]
                log_debug(f"[BATCH CACHE] Progetto {pid}: {_project_value_cache[pid]}")
            else:
                projects_to_fetch.append(pid)
    
    if not projects_to_fetch:
        log_debug(f"[BATCH] Tutti i {len(project_ids)} progetti già in cache")
        return result_values
    
    log_debug(f"[BATCH] Recuperando {len(projects_to_fetch)} progetti ({len(result_values)} dalla cache)")
    
    def fetch_single_project_value(project_id):
        """Funzione helper per fetch singolo progetto"""
        url = f"{config.REN_BASE_URL}/projects/{project_id}"
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.ok:
                project_data = response.json().get('data', {})
                value = project_data.get('project_total_price')
                
                # Aggiorna cache
                with _project_value_cache_lock:
                    _project_value_cache[project_id] = value
                
                return project_id, value
            else:
                log_warning(f"[BATCH] Errore HTTP {response.status_code} per progetto {project_id}")
                return project_id, None
        except Exception as e:
            log_warning(f"[BATCH] Errore progetto {project_id}: {e}")
            return project_id, None
    
    # Esecuzione batch con ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Suddividi in batch per evitare troppi thread
        batch_size = 5
        for i in range(0, len(projects_to_fetch), batch_size):
            batch = projects_to_fetch[i:i + batch_size]
            
            # Piccola pausa tra batch per rate limiting
            if i > 0:
                time.sleep(0.3)
            
            # Avvia fetch per questo batch
            futures = {executor.submit(fetch_single_project_value, pid): pid for pid in batch}
            
            # Raccogli risultati
            for future in as_completed(futures):
                project_id, value = future.result()
                result_values[project_id] = value
    
    log_debug(f"[BATCH] Completato: {len(result_values)} valori totali")
    return result_values


def get_projecttype_name_cached(type_id, headers):
    """Recupera il nome del tipo progetto con cache"""
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
    
    # Prova prima l'endpoint specifico per project status
    for endpoint in ["/projects/status", "/statuses"]:
        url = f"{config.REN_BASE_URL}{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.ok:
                data = response.json().get('data', [])
                status_map = {status['id']: status['name'] for status in data}
                with _cache_lock:
                    _status_cache.update(status_map)
                log_debug(f"✅ Caricati {len(status_map)} status da {endpoint}")
                return status_map
            else:
                log_debug(f"⚠️ Endpoint {endpoint} fallito: {response.status_code}")
        except Exception as e:
            log_debug(f"⚠️ Errore endpoint {endpoint}: {e}")
    
    log_error("❌ Nessun endpoint status funzionante trovato!")
    return {}


def get_project_subprojects_fast(project_ids, headers):
    """Recupera i subprojects di uno o più progetti con logging sintetico"""
    url = f"{config.REN_BASE_URL}/subprojects"
    
    # Permetti sia singolo id che lista
    if isinstance(project_ids, (str, int)):
        project_ids = [project_ids]
        
    params = []
    for pid in project_ids:
        params.append(("project", pid))
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=8)
        
        if response.ok:
            data = response.json().get('data', [])
            if isinstance(data, dict):
                data = [data]
            
            # OTTIMIZZAZIONE: Log sintetico solo se VERBOSE_MODE
            if VERBOSE_MODE:
                log_debug(f"[SUBPROJECTS] Trovati {len(data)} subprojects per {len(project_ids)} progetti")
                # Solo primi 3 subprojects per debug
                for sub in data[:3]:
                    pid = sub.get('project')
                    status = sub.get('status')
                    order = sub.get('order')
                    sub_id = sub.get('id')
                    value = sub.get('project_total_price')
                    log_debug(f"  - Subproject ID {sub_id} (project {pid}, order {order}): status={status}, value={value}")
                if len(data) > 3:
                    log_debug(f"  ... e altri {len(data) - 3} subprojects")
                
            return data
        elif response.status_code == 404:
            return []
        else:
            if VERBOSE_MODE:
                log_error(f"[SUBPROJECTS] Errore HTTP {response.status_code} per {project_ids}")
            return []
    except Exception as e:
        log_error(f"[SUBPROJECTS] Exception: {e}")
        return []


def get_customer_name_cached(customer_path, headers):
    """
    🚀 NUOVO: Recupera il nome del cliente con cache per migliorare performance
    
    Args:
        customer_path: Path del cliente (es. '/contacts/123')
        headers: Headers per API Rentman
        
    Returns:
        str: Nome del cliente o stringa vuota in caso di errore
    """
    if not customer_path:
        return ""
    
    customer_id = extract_id_from_path(customer_path)
    if not customer_id:
        return ""
    
    # Controlla cache
    with _customer_cache_lock:
        if customer_id in _customer_cache:
            return _customer_cache[customer_id]
    
    try:
        # Recupera dati cliente dall'API
        customer_url = f"{config.REN_BASE_URL}/contacts/{customer_id}"
        response = requests.get(customer_url, headers=headers, timeout=5)
        
        if response.ok:
            customer_data = response.json().get('data', {})
            # Prova displayname prima, poi name come fallback
            customer_name = customer_data.get('displayname') or customer_data.get('name', '')
            
            with _customer_cache_lock:
                _customer_cache[customer_id] = customer_name
            
            log_debug(f"[CUSTOMER] Recuperato nome cliente {customer_id}: '{customer_name}'")
            return customer_name
        else:
            log_warning(f"[CUSTOMER] Errore HTTP {response.status_code} per cliente {customer_id}")
    except Exception as e:
        log_warning(f"[CUSTOMER] Errore recuperando cliente {customer_id}: {e}")
    
    # Cache anche gli errori per evitare chiamate ripetute
    with _customer_cache_lock:
        _customer_cache[customer_id] = ""
    return ""


def preload_customers_batch(customer_paths, headers):
    """
    🚀 OTTIMIZZAZIONE: Precarica nomi clienti in batch parallelo con gestione rate limiting
    
    Args:
        customer_paths: Lista di path clienti da precaricare
        headers: Headers per le chiamate API
    """
    import time
    import random
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    if not customer_paths:
        return
    
    # Rimuovi duplicati mantenendo ordine
    unique_paths = list(dict.fromkeys(customer_paths))
    
    # Cache thread-safe per evitare chiamate duplicate
    local_cache = {}
    
    def load_customer_with_retry(path, max_retries=3, base_delay=1):
        """Carica cliente con retry logic per rate limiting"""
        if path in local_cache:
            return path, local_cache[path]
        
        for attempt in range(max_retries):
            try:
                url = f"{config.REN_BASE_URL}{path}"
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 429:  # Rate limit
                    # Calcola delay esponenziale: 1s, 2s, 4s
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    log_debug(f"⚠️  Rate limit per {path}, retry {attempt+1}/{max_retries} dopo {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                    
                elif response.ok:
                    customer_data = response.json().get('data', {})
                    name = customer_data.get('displayname', 'Nome non disponibile')
                    local_cache[path] = name
                    return path, name
                else:
                    log_debug(f"❌ Errore API per {path}: {response.status_code}")
                    break
                    
            except Exception as e:
                log_debug(f"❌ Errore caricamento {path} (tentativo {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (attempt + 1))
        
        # Se tutti i tentativi falliscono
        local_cache[path] = "Cliente non disponibile"
        return path, "Cliente non disponibile"
    
    log_debug(f"🚀 Precaricando {len(unique_paths)} clienti unici in batch (max 5 worker)...")
    start_time = time.time()
    
    # Riduco i worker da 10 a 5 per gestire meglio il rate limiting
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Suddividi in batch più piccoli per evitare troppi errori 429
        batch_size = 10
        futures = {}
        
        for i in range(0, len(unique_paths), batch_size):
            batch = unique_paths[i:i + batch_size]
            
            # Aggiungi small delay tra batch
            if i > 0:
                time.sleep(0.5)
            
            for path in batch:
                future = executor.submit(load_customer_with_retry, path)
                futures[future] = path
        
        # Raccogli risultati
        completed = 0
        for future in as_completed(futures):
            path, name = future.result()
            customer_name_cache[path] = name
            completed += 1
            
            if completed % 20 == 0:  # Log ogni 20 completamenti
                log_debug(f"  📊 Batch progress: {completed}/{len(unique_paths)} completati")
    
    elapsed = time.time() - start_time
    log_debug(f"✅ Batch clienti completato in {elapsed:.2f}s: {len(unique_paths)} clienti caricati")


def get_project_status_unified(project_id, headers, status_map, main_project=None, mode="normal"):
    """
    Recupera lo status del progetto usando logica unificata
    
    Args:
        project_id: ID del progetto
        headers: Headers per API Rentman
        status_map: Mappa degli status
        main_project: Dati del progetto principale (opzionale)
        mode: "normal" o "paginated" per logiche diverse
        
    Returns:
        str: Nome dello status del progetto
    """
    subprojects = get_project_subprojects_fast(project_id, headers)
    
    if subprojects:
        if mode == "paginated":
            # Modalità paginata: filtra solo subprojects con in_financial=True
            financial_subs = [s for s in subprojects if s.get('in_financial') is True]
            
            if financial_subs:
                subproject_principale = min(financial_subs, key=lambda s: s.get('order', 9999))
                status_path = subproject_principale.get('status')
                status_id = extract_id_from_path(status_path)
                value = subproject_principale.get('project_total_price')
                log_debug(f"[PROGETTO {project_id}] {mode.upper()} - Subproject finanziario: status_id={status_id}, value={value}")
                
                if status_id and status_id in status_map:
                    return status_map[status_id]
        else:
            # Modalità normale: usa subproject con order più basso
            subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
            status_path = subproject_principale.get('status')
            status_id = extract_id_from_path(status_path)
            value = subproject_principale.get('project_total_price')
            log_debug(f"[PROGETTO {project_id}] {mode.upper()} - Subproject principale: status_id={status_id}, value={value}")
            
            if status_id and status_id in status_map:
                return status_map[status_id]
    
    # Fallback: usa status del progetto principale
    if main_project:
        main_status_path = main_project.get('status')
        status_id = extract_id_from_path(main_status_path)
        value = main_project.get('project_total_price')
        log_debug(f"[PROGETTO {project_id}] {mode.upper()} - Status principale: status_id={status_id}, value={value}")
        
        if status_id and status_id in status_map:
            return status_map[status_id]
    
    return "Concept"


def process_project_unified(project_data, headers, status_map, start_dt, end_dt, debug_count, mode="normal"):
    """
    🚀 FUNZIONE UNIFICATA per processare un singolo progetto
    Include recupero del nome cliente per risolvere il problema nella griglia
    
    Args:
        project_data: Dati del progetto da processare
        headers: Headers per API Rentman
        status_map: Mappa degli status
        start_dt: Data di inizio filtro
        end_dt: Data di fine filtro
        debug_count: Contatore per debug
        mode: "normal" o "paginated" per logiche diverse
        
    Returns:
        dict: Dati processati del progetto con nome cliente
    """
    try:
        p = project_data
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        
        if not period_start or not period_end:
            return None
        
        # Filtro per date
        ps = datetime.fromisoformat(period_start[:10]).date()
        pe = datetime.fromisoformat(period_end[:10]).date()
        
        if pe < start_dt or ps > end_dt:
            return None
        
        project_id = p.get('id')
        project_type_path = p.get('project_type')
        project_type_id = extract_id_from_path(project_type_path)
        
        # Recupera status usando logica unificata
        project_status = get_project_status_unified(project_id, headers, status_map, main_project=p, mode=mode)
        
        # Gestione numero progetto
        raw_number = p.get("number")
        converted_number = str(raw_number) if raw_number is not None else "N/A"
        
        # Debug per primi progetti
        if debug_count[0] < 3:
            log_debug(f"🔍 Debug progetto {project_id}:")
            log_debug(f"  📝 Raw number field: {repr(raw_number)}")
            log_debug(f"  🔢 Number type: {type(raw_number)}")
            log_debug(f"  📄 Name: '{p.get('name')}'")
            log_debug(f"  📊 Status: '{project_status}'")
            log_debug(f"  🏷️ Project type ID: {project_type_id}")
            debug_count[0] += 1        # 🎯 ESTRAZIONE VALORE - NUOVA STRATEGIA CON RECUPERO SINGOLO
        project_value = None
        
        # 🚀 STRATEGIA 1: Cerca project_total_price nel progetto principale
        main_value = p.get('project_total_price')
        if main_value is not None and float(main_value) > 0:
            project_value = main_value
            log_debug(f"[PROGETTO {project_id}] ✅ project_total_price trovato nel progetto principale: {project_value}")
        else:
            log_debug(f"[PROGETTO {project_id}] ❌ progetto principale: project_total_price = {main_value}")
            
            # 🚀 STRATEGIA 2: Recupera valore da progetto singolo (NUOVA!)
            log_debug(f"[PROGETTO {project_id}] 🔄 Tentativo recupero da progetto singolo...")
            single_project_value = get_single_project_value(project_id, headers)
            
            if single_project_value is not None and float(single_project_value) > 0:
                project_value = single_project_value
                log_debug(f"[PROGETTO {project_id}] ✅ project_total_price trovato nel progetto singolo: {project_value}")
            else:
                log_debug(f"[PROGETTO {project_id}] ❌ progetto singolo: project_total_price = {single_project_value}")
                
                # 🚀 STRATEGIA 3: Cerca project_total_price nei subprojects (fallback)
                subprojects = get_project_subprojects_fast(project_id, headers)
                if subprojects:
                    log_debug(f"[PROGETTO {project_id}] Cercando project_total_price in {len(subprojects)} subprojects (fallback)...")
                    
                    # Priorità: subprojects con in_financial=True
                    financial_subs = [s for s in subprojects if s.get('in_financial') is True]
                    target_subs = financial_subs if financial_subs else subprojects
                    
                    for sub in sorted(target_subs, key=lambda s: s.get('order', 9999)):
                        sub_value = sub.get('project_total_price')
                        sub_id = sub.get('id')
                        
                        if sub_value is not None and float(sub_value) > 0:
                            project_value = sub_value
                            log_debug(f"[PROGETTO {project_id}] ✅ project_total_price trovato in subproject {sub_id}: {project_value}")
                            break
                        else:
                            log_debug(f"[PROGETTO {project_id}] ❌ subproject {sub_id}: project_total_price = {sub_value}")
                else:
                    log_debug(f"[PROGETTO {project_id}] ❌ Nessun subproject trovato")# 🔍 DEBUG: Log se ancora non trovato
        if project_value is None or str(project_value).strip() == '':
            log_warning(f"[WARN] project_total_price non trovato per progetto {project_id}")
            
            # 🔍 DEBUG COMPLETO: Mostra tutti i campi disponibili per i primi progetti
            if debug_count[0] < 3:
                log_debug(f"[PROGETTO {project_id}] DEBUG - project_total_price nel progetto principale:")
                main_price = p.get('project_total_price')
                log_debug(f"  🔑 project_total_price: {main_price} (tipo: {type(main_price)})")
                
                if subprojects:
                    log_debug(f"[PROGETTO {project_id}] DEBUG - project_total_price nei subprojects:")
                    for i, sub in enumerate(subprojects[:3]):
                        sub_price = sub.get('project_total_price')
                        sub_id = sub.get('id')
                        sub_order = sub.get('order')
                        in_financial = sub.get('in_financial')
                        log_debug(f"  📋 Sub {i+1} (ID:{sub_id}, order:{sub_order}, financial:{in_financial}): {sub_price} (tipo: {type(sub_price)})")
                else:
                    log_debug(f"[PROGETTO {project_id}] DEBUG - Nessun subproject disponibile")
        
        # 🚀 MIGLIORATA: Conversione valore più robusta
        try:
            if project_value is not None:
                # Converte in float prima, poi formatta
                numeric_value = float(project_value)
                formatted_value = '{:.2f}'.format(numeric_value)
                log_debug(f"[PROGETTO {project_id}] Valore convertito: {project_value} -> {formatted_value}")
            else:
                formatted_value = '0.00'
                log_debug(f"[PROGETTO {project_id}] Nessun valore trovato, usando default: {formatted_value}")
        except (ValueError, TypeError) as e:
            formatted_value = '0.00'
            log_warning(f"[PROGETTO {project_id}] Errore conversione valore '{project_value}': {e}")
        except Exception as e:
            formatted_value = '0.00'
            log_error(f"[PROGETTO {project_id}] Errore inaspettato conversione valore: {e}")
        
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
            else:
                log_warning(f"[WARN] account_manager_path presente ma manager_id non estratto per progetto {project_id}")
        else:
            log_warning(f"[WARN] Nessun account_manager per progetto {project_id}")
        
        # 🚀 NUOVO: Recupero nome cliente per risolvere il problema nella griglia
        customer_name = ""
        customer_path = p.get('customer')
        if customer_path:
            customer_name = get_customer_name_cached(customer_path, headers)
            log_debug(f"[PROGETTO {project_id}] Nome cliente: '{customer_name}'")
        else:
            log_warning(f"[WARN] Nessun customer associato al progetto {project_id}")
        
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
            "manager_email": manager_email,
            "contact_displayname": customer_name  # 🚀 NUOVO: Nome cliente per griglia
        }
        
    except Exception as e:
        log_error(f"Errore processando progetto {p.get('id', 'unknown')}: {e}")
        return None


def list_projects_by_date_unified(from_date, to_date, mode="normal"):
    """
    🚀 FUNZIONE UNIFICATA per recuperare progetti per data
    Consolida la logica di rentman_api.py e qb_customer.py
    INCLUDE: Ottimizzazione batch loading nomi clienti
    
    Args:
        from_date: Data di inizio (YYYY-MM-DD)
        to_date: Data di fine (YYYY-MM-DD)
        mode: "normal" o "paginated"
        
    Returns:
        list: Lista progetti con nomi clienti inclusi
    """
    log_info(f"🚀 Avvio recupero progetti unificato (modalità: {mode})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }

    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")    # Recupera progetti con VERA PAGINAZIONE (non patch)
    url = f"{config.REN_BASE_URL}/projects"
    log_debug(f"🔄 Recupero progetti con paginazione completa...")
    
    all_projects = []
    offset = 0
    limit = 150  # Ridotto da 300 per evitare errore 6MB dell'API
    
    while True:
        params = {
            'limit': limit,
            'offset': offset,
            'sort': '+id',  # Ordinamento consistente
            'fields': 'id,name,number,status,planperiod_start,planperiod_end,project_total_price,account_manager,project_type,customer,created,modified',  # Solo campi necessari per ridurre dimensioni response
            'id[gte]': 2900  # Filtro API diretto per ID >= 2900
        }
        
        log_debug(f"   📄 Pagina offset={offset}, limit={limit}")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if not response.ok:
            if offset == 0:
                # Se la prima pagina fallisce, è un errore critico
                raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
            else:
                # Se pagine successive falliscono, probabilmente non ci sono più dati
                log_debug(f"   ⏹️  Fine paginazione (HTTP {response.status_code})")
                break
        
        page_projects = response.json().get('data', [])
        
        if not page_projects:
            log_debug(f"   ⏹️  Fine paginazione (nessun progetto)")
            break
          all_projects.extend(page_projects)
        log_debug(f"   ✅ Recuperati {len(page_projects)} progetti (totale: {len(all_projects)})")
        
        # Se la pagina non è piena, probabilmente è l'ultima
        if len(page_projects) < limit:
            log_debug(f"   ⏹️  Ultima pagina (pagina parziale)")
            break
        
        offset += limit
        
        # Sicurezza: limite massimo per evitare loop infiniti
        if len(all_projects) > 10000:
            log_warning(f"⚠️  Limite sicurezza raggiunto: {len(all_projects)} progetti")
            break
    
    log_debug(f"📊 Progetti totali recuperati: {len(all_projects)}")
    
    # Il filtro GTR ID >= 2900 è ora fatto direttamente dall'API con id[gte]=2900
    
    projects = all_projects
    
    # Filtro date
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    log_debug(f"⏳ Filtraggio progetti per periodo {from_date} - {to_date}...")
    
    # 🚀 OTTIMIZZAZIONE: Precarica nomi clienti in batch prima del processing
    log_debug("👥 Precaricamento nomi clienti in batch...")
    customer_paths = [p.get('customer') for p in projects if p.get('customer')]
    if customer_paths:
        preload_customers_batch(customer_paths, headers)
        log_debug(f"✅ Precaricati {len(customer_paths)} nomi clienti in batch")
    
    # Processa progetti
    filtered = []
    debug_count = [0]
    
    for p in projects:
        result = process_project_unified(p, headers, status_map, start_dt, end_dt, debug_count, mode=mode)
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
            
            # Aggiorna i project type names
            for project in filtered:
                type_id = project['project_type_id']
                if type_id and type_id in type_name_futures:
                    try:
                        project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                    except:
                        project['project_type_name'] = ""
      # 🎯 NUOVO: Recupero batch valori mancanti 
    if filtered:
        log_debug("💰 Controllo valori mancanti per recupero batch...")
        projects_missing_values = []
        
        for project in filtered:
            try:
                value = float(project.get('project_value', '0.00'))
                if value <= 0:
                    projects_missing_values.append(project['id'])
            except (ValueError, TypeError):
                projects_missing_values.append(project['id'])
        
        if projects_missing_values:
            log_debug(f"🔄 Recupero batch valori per {len(projects_missing_values)} progetti...")
            batch_values = get_multiple_project_values_batch(projects_missing_values, headers)
              # Aggiorna valori nei progetti
            for project in filtered:
                project_id = project['id']
                if project_id in batch_values and batch_values[project_id] is not None:
                    try:
                        new_value = float(batch_values[project_id])
                        if new_value > 0:
                            project['project_value'] = f"{new_value:.2f}"
                            log_debug(f"[BATCH UPDATE] Progetto {project_id}: aggiornato valore a {new_value:.2f}")
                    except (ValueError, TypeError) as e:
                        log_debug(f"[BATCH UPDATE] Errore conversione valore progetto {project_id}: {e}")
            
            log_debug(f"✅ Batch valori completato: {len([v for v in batch_values.values() if v is not None])} valori aggiornati")
        else:
            log_debug("✅ Tutti i progetti hanno già valori validi")
    
    log_info(f"🎉 Completato! Restituiti {len(filtered)} progetti con nomi clienti e valori")
    return filtered


def list_projects_by_date_paginated_unified(from_date, to_date, page_size=20):
    """
    🚀 FUNZIONE UNIFICATA per recupero progetti paginato
    Generator che yield pagine di progetti processati
    INCLUDE: Ottimizzazione batch loading nomi clienti per pagina
    
    Args:
        from_date: Data di inizio (YYYY-MM-DD)
        to_date: Data di fine (YYYY-MM-DD)
        page_size: Numero progetti per pagina
        
    Yields:
        dict: Dati pagina con progetti processati
    """
    log_info(f"🚀 Avvio recupero progetti paginato unificato (pagine da {page_size})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")    # Recupera progetti con VERA PAGINAZIONE (non patch)    url = f"{config.REN_BASE_URL}/projects"
    log_debug(f"🔄 Recupero progetti con paginazione completa...")
    
    all_projects = []
    offset = 0
    limit = 150  # Ridotto da 300 per evitare errore 6MB dell'API
    
    while True:
        params = {
            'limit': limit,
            'offset': offset,
            'sort': '+id',  # Ordinamento consistente
            'fields': 'id,name,number,status,planperiod_start,planperiod_end,project_total_price,account_manager,project_type,customer,created,modified',  # Solo campi necessari per ridurre dimensioni response
            'id[gte]': 2900  # Filtro API diretto per ID >= 2900
        }
        
        log_debug(f"   📄 Pagina offset={offset}, limit={limit}")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if not response.ok:
            if offset == 0:
                # Se la prima pagina fallisce, è un errore critico
                raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
            else:
                # Se pagine successive falliscono, probabilmente non ci sono più dati
                log_debug(f"   ⏹️  Fine paginazione (HTTP {response.status_code})")            break
        
        page_projects = response.json().get('data', [])
        
        if not page_projects:
            log_debug(f"   ⏹️  Fine paginazione (nessun progetto)")
            break
        
        all_projects.extend(page_projects)
        log_debug(f"   ✅ Recuperati {len(page_projects)} progetti (totale: {len(all_projects)})")
        
        # Se la pagina non è piena, probabilmente è l'ultima
        if len(page_projects) < limit:
            log_debug(f"   ⏹️  Ultima pagina (pagina parziale)")
            break
        
        offset += limit
        
        # Sicurezza: limite massimo per evitare loop infiniti
        if len(all_projects) > 10000:
            log_warning(f"⚠️  Limite sicurezza raggiunto: {len(all_projects)} progetti")
            break
    
    log_debug(f"📊 Progetti totali recuperati con paginazione: {len(all_projects)}")

    # Il filtro GTR ID >= 2900 è ora fatto direttamente dall'API con id[gte]=2900

    # Pre-filtra progetti per date
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    
    date_filtered_projects = []
    for p in all_projects:
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
    
    # 🚀 OTTIMIZZAZIONE: Precarica nomi clienti in batch per TUTTA la lista prima della paginazione
    customer_paths = [p.get('customer') for p in date_filtered_projects if p.get('customer')]
    if customer_paths:
        log_debug(f"🚀 Precaricando {len(customer_paths)} nomi clienti in batch prima della paginazione...")
        preload_customers_batch(customer_paths, headers)
    
    log_debug(f"✅ Progetti nel periodo: {len(date_filtered_projects)}")
    
    # Processa progetti a pagine
    debug_count = [0]
    total_processed = 0
    total_projects = len(date_filtered_projects)  # 🔧 FIX: Calcola lunghezza una volta
    
    for i in range(0, total_projects, page_size):
        page_projects = date_filtered_projects[i:i + page_size]
        page_num = (i // page_size) + 1
        
        log_debug(f"📄 Processando pagina {page_num} ({len(page_projects)} progetti)...")
        
        # 🚀 OTTIMIZZAZIONE: Precarica nomi clienti per questa pagina
        page_customer_paths = [p.get('customer') for p in page_projects if p.get('customer')]
        if page_customer_paths:
            preload_customers_batch(page_customer_paths, headers)
            log_debug(f"👥 Precaricati {len(page_customer_paths)} nomi clienti per pagina {page_num}")
        
        page_results = []
        for p in page_projects:
            result = process_project_unified(p, headers, status_map, start_dt, end_dt, debug_count, mode="paginated")
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
            'has_more': (i + page_size) < total_projects  # 🔧 FIX: Usa variabile calcolata
        }
    
    log_debug(f"🎉 Paginazione completata! {total_processed} progetti totali processati")


def list_projects_by_date_paginated_full_unified(from_date, to_date, page_size=20):
    """
    🚀 VERSIONE UNIFICATA che restituisce tutti i progetti paginati come lista completa
    Include filtro stati finale per compatibilità
    
    Args:
        from_date: Data di inizio (YYYY-MM-DD)
        to_date: Data di fine (YYYY-MM-DD)
        page_size: Numero progetti per pagina
        
    Returns:
        list: Lista completa progetti filtrati con nomi clienti    """
    all_projects = []
    
    for page_data in list_projects_by_date_paginated_unified(from_date, to_date, page_size):
        all_projects.extend(page_data['projects'])
        log_debug(f"📊 Progresso: {page_data['total_processed']} progetti caricati...")
    
    # Applica filtro stati finale (SOLO stati validi)
    log_debug(f"⏳ Applicando filtro stati finale su {len(all_projects)} progetti processati...")
    stati_validi = {
        'confermato', 'confirmed',
        'in location', 'on location',
        'rientrato', 'returned',
        # Includi progetti con status problematici per debug
        'n/a', 'none', ''
    }
    
    # Debug: mostra stati prima del filtro
    stati_presenti = set()
    for p in all_projects:
        stati_presenti.add(p.get('status', 'NESSUNO'))
    log_debug(f"🔍 Stati presenti prima del filtro finale: {sorted(stati_presenti)}")    # Filtra SOLO i progetti con stati validi (più permissivo per status mancanti)
    progetti_validi = []
    
    for p in all_projects:
        project_id = p.get('id', 0)
        status = p.get('status', '').lower().strip()
        
        # Includi progetti con status validi O con status mancanti/problematici
        if (status in stati_validi or 
            not status or 
            status == 'none' or 
            status == 'n/a'):
            
            progetti_validi.append(p)
            log_debug(f"  ✅ VALIDO - Progetto {project_id} con status '{p.get('status')}'")
        else:
            log_debug(f"  🚫 ESCLUSO - Progetto {project_id} con status '{p.get('status')}' (non negli stati validi)")
    
    log_debug(f"📊 Progetti validi finali: {len(progetti_validi)}")
    
    return progetti_validi


def get_project_and_customer_unified(project_id):
    """
    🚀 FUNZIONE UNIFICATA per recuperare progetto e cliente
    
    Args:
        project_id: ID del progetto da recuperare
        
    Returns:
        dict: Dizionario con chiavi 'project' e 'customer'
    """
    log_info(f"📊 Recupero progetto {project_id} e cliente associato...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    try:
        # Recupera il progetto
        url = f"{config.REN_BASE_URL}/projects/{project_id}"
        response = requests.get(url, headers=headers)
        
        if not response.ok:
            raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
        
        project = response.json().get('data', {})
        if not project:
            raise Exception(f"Progetto {project_id} non trovato")
        
        # Recupera il cliente associato
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
        
        log_info(f"✅ Recuperati dati di progetto {project_id} e cliente {customer_id}")
        
        return {
            "project": project,
            "customer": customer
        }
        
    except Exception as e:
        log_error(f"Errore recuperando progetto {project_id}: {e}")
        raise


def clear_cache():
    """
    🚀 FUNZIONE UNIFICATA per svuotare tutte le cache
    Include la nuova cache clienti
    """
    global _projecttype_cache, _status_cache, _manager_cache, _customer_cache
    
    with _cache_lock:
        _projecttype_cache.clear()
        _status_cache.clear()
    
    with _manager_cache_lock:
        _manager_cache.clear()
    
    with _customer_cache_lock:
        _customer_cache.clear()
    
    log_info("🧹 Tutte le cache unificate svuotate")


# Alias per compatibilità con i moduli esistenti
list_projects_by_date = list_projects_by_date_unified
list_projects_by_date_paginated_full = list_projects_by_date_paginated_full_unified
get_project_and_customer = get_project_and_customer_unified
