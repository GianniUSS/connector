import requests
import config
from datetime import datetime

def list_projects_by_date(from_date, to_date):
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/projects"
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    projects = response.json().get('data', [])
    # DEBUG: Stampa primi 2 progetti e relative chiavi
    for i, p in enumerate(projects[:2]):
        print(f"DEBUG PROGETTO {i+1}: {p}")
        print(f"CHIAVI DISPONIBILI: {list(p.keys())}")

    # Filtro solito (può restituire 0, non importa ora)
    fmt = '%Y-%m-%d'
    start_dt = datetime.strptime(from_date, fmt).date()
    end_dt   = datetime.strptime(to_date, fmt).date()
    filtered = []
    for p in projects:
        proj_start = p.get('start')
        proj_end   = p.get('end')
        if not proj_start or not proj_end:
            continue
        try:
            ps = datetime.fromisoformat(proj_start[:10]).date()
            pe = datetime.fromisoformat(proj_end[:10]).date()
        except ValueError:
            continue
        if not (pe < start_dt or ps > end_dt):
            filtered.append(p)
    print(f"DEBUG: Progetti dopo filtraggio: {len(filtered)}")
    return filtered