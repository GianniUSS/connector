import requests
import config
from rentman_api import get_project_subprojects_fast, get_all_statuses, extract_id_from_path

def test_subproject_statuses(project_id):
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    # Recupera la mappa degli status
    status_map = get_all_statuses(headers)
    # Recupera i subprojects tramite API dedicata
    subprojects = get_project_subprojects_fast(project_id, headers)
    if not subprojects:
        print(f"Nessun subproject trovato per il progetto {project_id}")
        return
    print(f"Trovati {len(subprojects)} subprojects per il progetto {project_id}:")
    for sub in subprojects:
        sub_id = sub.get('id')
        status_path = sub.get('status')
        status_id = extract_id_from_path(status_path)
        status_name = status_map.get(status_id, 'Concept')
        print(f"Subproject ID: {sub_id}, Status: {status_name} (ID: {status_id})")

if __name__ == "__main__":
    test_subproject_statuses(3739)
