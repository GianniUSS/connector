import requests
import config

def get_project_and_customer(projectId):
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    proj_url = f"{config.REN_BASE_URL}/projects/{projectId}"
    proj_res = requests.get(proj_url, headers=headers)
    if not proj_res.ok:
        raise Exception(f"Rentman API Error {proj_res.status_code}: {proj_res.text}")
    proj_payload = proj_res.json()
    project = proj_payload.get('data')
    cust_path = project.get('customer')
    if not cust_path:
        raise Exception(f"Nessun customer associato al Progetto {projectId}")
    cust_url = f"{config.REN_BASE_URL}{cust_path}"
    cust_res = requests.get(cust_url, headers=headers)
    if not cust_res.ok:
        raise Exception(f"Rentman API Error {cust_res.status_code}: {cust_res.text}")
    cust_payload = cust_res.json()
    customer = cust_payload.get('data')
    return {'project': project, 'customer': customer}
