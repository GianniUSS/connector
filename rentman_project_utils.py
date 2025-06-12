"""
Funzioni riutilizzabili per filtro progetti Rentman (data, stato, dettagli)
"""
import requests
from datetime import datetime

def extract_id_from_path(path):
    if not path:
        return None
    try:
        return int(path.split('/')[-1])
    except (ValueError, IndexError):
        return None

def filter_projects_by_date(projects, from_date, to_date, verbose=False):
    """Filtra i progetti che si sovrappongono all'intervallo from_date → to_date. Se verbose=True, stampa il totale progetti prima e dopo il filtro."""
    from datetime import datetime
    start_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    if verbose:
        print(f"[INFO] Progetti totali PRIMA filtro data: {len(projects)}")
    filtered = []
    for p in projects:
        period_start = p.get('planperiod_start')
        period_end = p.get('planperiod_end')
        if not period_start or not period_end:
            continue
        try:
            ps = datetime.fromisoformat(period_start[:10]).date()
            pe = datetime.fromisoformat(period_end[:10]).date()
            if not (pe < start_dt or ps > end_dt):
                filtered.append(p)
        except Exception:
            continue
    if verbose:
        print(f"[INFO] Progetti totali DOPO filtro data: {len(filtered)}")
    return filtered

def get_status_map(headers, base_url):
    url = f"{base_url}/statuses"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json().get('data', [])
        return {s['id']: s['name'] for s in data}
    return {}

def get_project_status(project_id, headers, status_map, base_url, subprojects=None):
    """
    Determina lo status di un progetto:
    - Cerca primo subproject con in_financial=True
    - Se non trovato, usa lo status del progetto principale
    """
    if not subprojects:
        sub_url = f"{base_url}/subprojects?project={project_id}"
        sub_resp = requests.get(sub_url, headers=headers, timeout=10)
        subprojects = sub_resp.json().get('data', []) if sub_resp.ok else []
        if isinstance(subprojects, dict):
            subprojects = [subprojects]
    sub_fin = [s for s in subprojects if s.get('in_financial') is True]
    if sub_fin:
        sub = min(sub_fin, key=lambda s: s.get('order', 9999))
        status_path = sub.get('status')
        status_id = extract_id_from_path(status_path)
        return status_map.get(status_id, "Sconosciuto")
    project_url = f"{base_url}/projects/{project_id}"
    resp = requests.get(project_url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json().get('data', {})
        status_path = data.get('status')
        status_id = extract_id_from_path(status_path)
        return status_map.get(status_id, "Sconosciuto")
    return "Sconosciuto"

def filter_projects_by_status(projects, headers, stati_interesse, base_url):
    """Filtra i progetti per stati di interesse usando la logica subprojects"""
    status_map = get_status_map(headers, base_url)
    stati_set = set(s.lower() for s in stati_interesse)
    filtered = []
    for p in projects:
        project_id = p.get('id')
        status_name = get_project_status(project_id, headers, status_map, base_url)
        if status_name.lower() in stati_set:
            filtered.append((p, status_name))
    return filtered
