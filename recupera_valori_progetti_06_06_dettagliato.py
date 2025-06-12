import requests
import config

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

project_ids = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]
headers = {
    'Authorization': f'Bearer {config.REN_API_TOKEN}',
    'Accept': 'application/json'
}
status_map = get_status_map(headers)

for pid in project_ids:
    url = f"{config.REN_BASE_URL}/projects/{pid}"
    resp = requests.get(url, headers=headers, timeout=10)
    if not resp.ok:
        print(f"ID: {pid} | ERRORE HTTP {resp.status_code}")
        continue
    data = resp.json().get('data', {})
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
        valore = sub.get('project_total_price')
        status_path = sub.get('status')
        status_id = extract_id_from_path(status_path)
        status_name = status_map.get(status_id, status_id)
        print(f"ID: {pid} | Valore subproject: {valore} | Status: {status_name} | Nome: {data.get('name')}")
    else:
        valore = data.get('project_total_price')
        status_path = data.get('status')
        status_id = extract_id_from_path(status_path)
        status_name = status_map.get(status_id, status_id)
        print(f"ID: {pid} | Valore progetto: {valore} | Status: {status_name} | Nome: {data.get('name')}")
