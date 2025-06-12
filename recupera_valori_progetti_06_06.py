import requests
import config

# Lista degli ID dei progetti trovati per il 06/06
project_ids = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]

headers = {
    'Authorization': f'Bearer {config.REN_API_TOKEN}',
    'Accept': 'application/json'
}

for pid in project_ids:
    url = f"{config.REN_BASE_URL}/projects/{pid}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.ok:
        data = resp.json().get('data', {})
        print(f"ID: {pid} | project_total_price: {data.get('project_total_price')} | Nome: {data.get('name')}")
    else:
        print(f"ID: {pid} | ERRORE HTTP {resp.status_code}")
