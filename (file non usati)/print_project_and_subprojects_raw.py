import requests
import config
import json
from rentman_api import get_all_statuses, extract_id_from_path

def main():
    project_id = 3618
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    # Recupera il progetto principale
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"Rentman API Error {response.status_code}: {response.text}")
        return
    project = response.json().get('data', {})
    print("\n--- PAYLOAD RAW PROGETTO PRINCIPALE ---")
    print(json.dumps(project, indent=2, ensure_ascii=False))

    # Recupera la mappa degli status
    status_map = get_all_statuses(headers)

    # Recupera i subprojects tramite endpoint corretto (query param project)
    url_sub = f"{config.REN_BASE_URL}/subprojects"
    params = {'project': project_id}
    response_sub = requests.get(url_sub, headers=headers, params=params)
    if not response_sub.ok:
        print(f"Rentman API Error (subprojects) {response_sub.status_code}: {response_sub.text}")
        return
    subprojects = response_sub.json().get('data', [])
    print("\n--- PAYLOAD RAW SUBPROJECTS ---")
    # Gestione uniforme: se dict, converto in lista
    if isinstance(subprojects, dict):
        subprojects = [subprojects]
    if isinstance(subprojects, list):
        if subprojects:
            for i, sub in enumerate(subprojects, 1):
                print(f"\nSubproject {i}:")
                print(json.dumps(sub, indent=2, ensure_ascii=False))
                # Stampa stato leggibile
                status_path = sub.get('status')
                status_id = extract_id_from_path(status_path)
                status_name = status_map.get(status_id, 'Concept')
                print(f"  Stato leggibile: {status_name} (ID: {status_id}) [raw: {status_path}]")
        else:
            print("[INFO] Nessun subproject trovato (lista vuota)")
    else:
        print(f"[INFO] subprojects non è una lista: {type(subprojects)} -> {subprojects}")

if __name__ == "__main__":
    main()
