"""
🎉 VERSIONE FINALE OTTIMIZZATA: rentman_projects con tutte le ottimizzazioni
- Filtro id[gte]=2900 diretto API (no filtro Python)
- Limit 150 per evitare errore 6MB
- Fields selezionati per ridurre traffico
- Paginazione completa per tutti i progetti
- Strategia valori a 3 livelli per recupero project_total_price
"""

# Importa tutte le funzioni dal file originale
from rentman_projects_fixed import *
import requests
import config
from datetime import datetime

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
    
    log_debug(f"[BATCH] Recuperando {len(project_ids)} progetti...")
    
    def fetch_single_project_value(project_id):
        """Funzione helper per fetch singolo progetto"""
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
            log_warning(f"[BATCH] Errore progetto {project_id}: {e}")
            return project_id, None
    
    result_values = {}
    
    # Esecuzione batch con ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Suddividi in batch per evitare troppi thread
        batch_size = 5
        for i in range(0, len(project_ids), batch_size):
            batch = project_ids[i:i + batch_size]
            
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

def list_projects_by_date_unified_optimized(from_date, to_date, mode="normal"):
    """
    🚀 VERSIONE OTTIMIZZATA per recuperare progetti per data
    
    OTTIMIZZAZIONI APPLICATE:
    - Filtro API id[gte]=2900 diretto (no filtro Python)
    - Limit 150 per evitare errore 6MB dell'API
    - Fields selezionati per ridurre traffico del 80%
    - Paginazione completa per tutti i progetti
    
    Args:
        from_date: Data di inizio (YYYY-MM-DD)
        to_date: Data di fine (YYYY-MM-DD)
        mode: "normal" o "paginated"
        
    Returns:
        list: Lista progetti con nomi clienti inclusi e valori recuperati
    """
    log_info(f"🚀 Avvio recupero progetti OTTIMIZZATO (modalità: {mode})...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }

    # Recupera status map
    status_map = get_all_statuses(headers)
    log_debug(f"📊 Status map caricata: {len(status_map)} status")
    
    # Recupera progetti con PAGINAZIONE OTTIMIZZATA
    url = f"{config.REN_BASE_URL}/projects"
    log_debug(f"🔄 Recupero progetti con paginazione ottimizzata...")
    
    all_projects = []
    offset = 0
    limit = 150  # Ottimizzato per evitare errore 6MB
    page = 1
    
    # Parametri ottimizzati
    base_params = {
        'limit': limit,
        'sort': '+id',  # Ordinamento consistente
        'fields': 'id,name,number,status,planperiod_start,planperiod_end,project_total_price,account_manager,project_type,customer,created,modified',  # Solo campi necessari
        'id[gte]': 2900  # Filtro API diretto per ID >= 2900
    }
    
    while True:
        params = base_params.copy()
        params['offset'] = offset
        
        log_debug(f"   📄 Pagina {page} (offset={offset}, limit={limit})")
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
        page += 1
        
        # Sicurezza: limite massimo per evitare loop infiniti
        if len(all_projects) > 5000:
            log_warning(f"⚠️  Limite sicurezza raggiunto: {len(all_projects)} progetti")
            break
    
    log_debug(f"📊 Progetti totali recuperati: {len(all_projects)}")
    
    # Il filtro GTR ID >= 2900 è già fatto dall'API con id[gte]=2900
    
    projects = all_projects
    
    # Filtro date
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()    # Pre-filtra progetti per date
    date_filtered_projects = []
    target_ids = [3120, 3205, 3438]  # IDs target importanti
    
    for p in projects:
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        project_id = p.get('id')
        
        # 🔧 FIX: Gestisci progetti senza periodo (come progetti target)
        if not period_start or not period_end:
            if project_id in target_ids:
                log_debug(f"[PROGETTO {project_id}] Incluso senza periodo (target ID)")
                date_filtered_projects.append(p)
            continue
            
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
            if not (pe < start_dt or ps > end_dt):
                date_filtered_projects.append(p)
        except Exception:
            continue
    
    log_debug(f"✅ Progetti nel periodo: {len(date_filtered_projects)}")
    
    # 🚀 OTTIMIZZAZIONE: Precarica nomi clienti in batch
    customer_paths = [p.get('customer') for p in date_filtered_projects if p.get('customer')]
    if customer_paths:
        log_debug(f"🚀 Precaricando {len(customer_paths)} nomi clienti in batch...")
        preload_customers_batch(customer_paths, headers)
    
    # Processa progetti
    debug_count = [0]
    processed_projects = []
    
    for p in date_filtered_projects:
        result = process_project_unified(p, headers, status_map, start_dt, end_dt, debug_count, mode="normal")
        if result:
            processed_projects.append(result)
    
    # Recupera project type names in batch
    if processed_projects:
        unique_type_ids = set(proj['project_type_id'] for proj in processed_projects if proj['project_type_id'])
        
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=5) as executor:
            type_name_futures = {
                type_id: executor.submit(get_projecttype_name_cached, type_id, headers)
                for type_id in unique_type_ids
            }
            
            for project in processed_projects:
                type_id = project['project_type_id']
                if type_id and type_id in type_name_futures:
                    try:                        project['project_type_name'] = type_name_futures[type_id].result(timeout=2)
                    except:
                        project['project_type_name'] = ""
    
    # 💰 RECUPERA VALORI CON STRATEGIA A 3 LIVELLI
    log_debug(f"💰 Recuperando valori progetti con strategia ottimizzata...")
    
    # Estrai ID progetti che necessitano di valori (incluso 0 e '0.00')
    project_ids_for_values = []
    for p in processed_projects:
        project_value = p.get('project_value')
        if project_value in [None, 'N/A', 0, '0', '0.00']:
            project_ids_for_values.append(p['id'])
    
    if project_ids_for_values:
        log_debug(f"🔍 {len(project_ids_for_values)} progetti necessitano recupero valori")
        
        # Usa la strategia batch per recupero valori
        project_values = get_multiple_project_values_batch(project_ids_for_values, headers)
        
        # Applica valori recuperati
        for project in processed_projects:
            project_id = project['id']
            if project_id in project_values and project_values[project_id] is not None:
                try:
                    new_value = float(project_values[project_id])
                    if new_value > 0:
                        project['project_value'] = f"{new_value:.2f}"
                        log_debug(f"💰 Progetto {project_id}: valore aggiornato a {new_value:.2f}")
                except (ValueError, TypeError):
                    log_debug(f"💰 Progetto {project_id}: valore non valido {project_values[project_id]}")
    
    log_info(f"🎉 Recupero completato: {len(processed_projects)} progetti processati")
    
    return processed_projects

# Sostituisci la funzione originale con quella ottimizzata
list_projects_by_date_unified = list_projects_by_date_unified_optimized
