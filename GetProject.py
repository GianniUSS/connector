import sys
import requests
import config
from rentman_api import get_all_statuses, get_project_subprojects_fast, extract_id_from_path

def get_project_and_customer(project_id):
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Rentman API Error {response.status_code}: {response.text}")
    project = response.json().get('data', {})
    customer_path = project.get('customer')
    if not customer_path:
        raise Exception(f"Nessun customer associato al progetto {project_id}")
    cust_url = f"{config.REN_BASE_URL}{customer_path}"
    cust_res = requests.get(cust_url, headers=headers)
    if not cust_res.ok:
        raise Exception(f"Rentman API Error {cust_res.status_code}: {cust_res.text}")
    customer = cust_res.json().get('data', {})
    return {'project': project, 'customer': customer}

def main():
    if len(sys.argv) < 2:
        print("Uso: python GetProject.py <project_id>")
        return
    project_id = sys.argv[1]
    try:
        data = get_project_and_customer(project_id)
        project = data['project']
        customer = data['customer']
        print(f"\n=== PROGETTO PRINCIPALE ===\nID: {project.get('id')}\nNome: {project.get('name')}\nNumero: {project.get('number')}\nCliente: {customer.get('name')}")
        # Recupera subprojects
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        subprojects = get_project_subprojects_fast(project_id, headers)
        status_map = get_all_statuses(headers)
        sub_status = None
        sub_status_id = None
        subproject_principale = None
        if subprojects:
            # Trova il subproject con order più basso
            subproject_principale = min(subprojects, key=lambda s: s.get('order', 9999))
            sub_status_path = subproject_principale.get('status')
            sub_status_id = extract_id_from_path(sub_status_path)
            if sub_status_id and sub_status_id in status_map:
                sub_status = status_map[sub_status_id]
        main_status_path = project.get('status')
        main_status_id = extract_id_from_path(main_status_path)
        print(f"[DEBUG] Progetto principale status raw: {main_status_path}, estratto ID: {main_status_id}")
        if sub_status:
            main_status = sub_status
            print(f"Stato progetto (subproject con order più basso): {main_status} (ID: {sub_status_id})")
        else:
            main_status = status_map.get(main_status_id, 'Concept')
            print(f"Stato progetto (dal progetto principale): {main_status} (ID: {main_status_id})")
            if main_status_id not in status_map:
                print(f"⚠️  ID status {main_status_id} non trovato nella mappa status. Verrà mostrato 'Concept'.")
        # Stampa subprojects
        if subprojects:
            print(f"\n--- SUBPROJECTS ({len(subprojects)}) ---")
            for i, sub in enumerate(subprojects, 1):
                sub_id = sub.get('id')
                sub_name = sub.get('name')
                sub_status_path = sub.get('status')
                sub_status_id = extract_id_from_path(sub_status_path)
                sub_status = status_map.get(sub_status_id, 'Concept')
                print(f"{i}) ID: {sub_id} | Nome: {sub_name} | Stato: {sub_status} (ID: {sub_status_id}) [raw: {sub_status_path}] | order: {sub.get('order')}")
        else:
            print("\nNessun subproject trovato per questo progetto.")
        # Stampa subprojects dettagliati
        if subprojects:
            print(f"\n--- SUBPROJECTS ({len(subprojects)}) ---")
            for i, sub in enumerate(subprojects, 1):
                print(f"\nSubproject {i} (ID: {sub.get('id')}):")
                for k, v in sub.items():
                    print(f"  {k}: {v}")
        else:
            print("\nNessun subproject trovato per questo progetto.")
        # Stampa dettagliata di tutti i campi del progetto principale
        print("\n--- DETTAGLIO PROGETTO PRINCIPALE ---")
        for k, v in project.items():
            print(f"  {k}: {v}")
        # Stampa la mappa degli status per debug
        print("\nMappa status Rentman (ID -> Nome):")
        for sid, sname in status_map.items():
            print(f"  {sid}: {sname}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    main()
