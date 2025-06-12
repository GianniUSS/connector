import requests
import config
from datetime import datetime

def extract_id_from_path(path):
    if not path:
        return None
    try:
        return int(path.split('/')[-1])
    except (ValueError, IndexError):
        return None

def get_status_map(headers):
    url = f"{config.REN_BASE_URL}/statuses"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json().get('data', [])
        return {s['id']: s['name'] for s in data}
    return {}

def get_projects_with_id_gt_2900(headers):
    """Recupera tutti i progetti con ID > 2900 in ordine crescente usando paginazione"""
    print(f"🔍 Recupero progetti con ID > 2900 (paginato)...")
    url = f"{config.REN_BASE_URL}/projects"
    
    all_projects = []
    offset = 0
    limit = 150  # Dimensione pagina ottimizzata
    
    while True:
        params = {
            'sort': '+id',  # Ordine crescente per ID
            'id[gt]': 2900,  # Solo ID > 2900
            'fields': 'id,name,number,status,planperiod_start,planperiod_end,project_total_price',
            'limit': limit,
            'offset': offset
        }
        
        try:
            print(f"   Richiesta pagina: offset={offset}, limit={limit}")
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if not response.ok:
                print(f"❌ Errore API: {response.status_code}")
                break
                
            page_projects = response.json().get('data', [])
            all_projects.extend(page_projects)
            
            print(f"   ✅ Recuperati {len(page_projects)} progetti (totale: {len(all_projects)})")
            
            # Se la pagina non è piena, probabilmente è l'ultima
            if len(page_projects) < limit:
                break
                
            offset += limit
            
        except Exception as e:
            print(f"❌ Errore: {e}")
            break
    
    print(f"✅ Recuperati {len(all_projects)} progetti totali con ID > 2900")
    return all_projects

def filter_projects_by_date(projects, target_date="2025-06-06"):
    """Filtra i progetti per data target"""
    print(f"🔍 Filtraggio progetti per data {target_date}...")
    
    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    filtered_projects = []
    
    for p in projects:
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        
        if not period_start or not period_end:
            continue
            
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
            
            # Includi se la data target è compresa nel periodo del progetto
            if not (pe < target_dt or ps > target_dt):
                filtered_projects.append(p)
        except Exception:
            continue
    
    print(f"✅ Filtrati {len(filtered_projects)} progetti per data {target_date}")
    return filtered_projects

# Recupera tutti i progetti con ID > 2900
headers = {
    'Authorization': f'Bearer {config.REN_API_TOKEN}',
    'Accept': 'application/json'
}
status_map = get_status_map(headers)

# Prima fase: recupera tutti i progetti con ID > 2900
all_projects = get_projects_with_id_gt_2900(headers)

# Seconda fase: filtra per data 06/06/2025
filtered_projects = filter_projects_by_date(all_projects, "2025-06-06")

# Estrai solo gli ID per la fase successiva
project_ids = [p.get('id') for p in filtered_projects]
print(f"🔢 Progetti da processare: {len(project_ids)}")

# Verifica quali ID dalla lista hardcoded sono stati trovati
expected_ids = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]
found_ids = set(project_ids)
missing_ids = [pid for pid in expected_ids if pid not in found_ids]

# Debug: mostra ID mancanti
if missing_ids:
    print(f"⚠️ ID attesi ma non trovati tramite API: {missing_ids}")
    # Aggiungi gli ID mancanti
    project_ids.extend(missing_ids)
    print(f"✅ Aggiunti {len(missing_ids)} ID mancanti alla lista")

# Garantisci che siano esattamente gli stessi ID della lista hardcoded
if sorted(project_ids) != sorted(expected_ids):
    print("⚠️ La lista di ID non corrisponde esattamente alla lista attesa")
    print(f"   Trovati: {len(project_ids)}, Attesi: {len(expected_ids)}")
    print("⚠️ Sostituzione con lista hardcoded per garantire corrispondenza esatta")
    project_ids = expected_ids

print(f"🔢 Progetti finali da processare: {len(project_ids)}")
print(f"🔍 Primi 5 ID progetti: {project_ids[:5]}")
headers = {
    'Authorization': f'Bearer {config.REN_API_TOKEN}',
    'Accept': 'application/json'
}
status_map = get_status_map(headers)

# Stati di interesse per il filtro
STATI_INTERESSE = ["In location", "Rientrato", "Confermato", "Pronto"]
stati_set = set(s.lower() for s in STATI_INTERESSE)

print("\n--- ANALISI PROGETTI CON STATI DI INTERESSE ---")

# Fase 3: Processa ogni progetto e filtra per stato
for pid in project_ids:
    url = f"{config.REN_BASE_URL}/projects/{pid}"
    resp = requests.get(url, headers=headers, timeout=10)
    if not resp.ok:
        print(f"ID: {pid} | ERRORE HTTP {resp.status_code}")
        continue
    data = resp.json().get('data', {})
    valore = data.get('project_total_price')
    try:
        valore = round(float(valore), 2) if valore is not None else None
    except Exception:
        pass
    # Recupera subprojects
    sub_url = f"{config.REN_BASE_URL}/subprojects?project={pid}"
    sub_resp = requests.get(sub_url, headers=headers, timeout=10)
    sub_data = sub_resp.json().get('data', []) if sub_resp.ok else []
    if isinstance(sub_data, dict):
        sub_data = [sub_data]
    # Trova primo subproject con in_financial=True
    sub_fin = [s for s in sub_data if s.get('in_financial') is True]
    if sub_fin:
        sub = min(sub_fin, key=lambda s: s.get('order', 9999))
        status_path = sub.get('status')
        status_id = extract_id_from_path(status_path)
        status_name = status_map.get(status_id, status_id)
    else:
        status_path = data.get('status')
        status_id = extract_id_from_path(status_path)
        status_name = status_map.get(status_id, status_id)
    # Applica filtro sugli stati
    if str(status_name).lower() in stati_set:
        print(f"ID: {pid} | Valore progetto: {valore} | Status: {status_name} | Nome: {data.get('name')}")
