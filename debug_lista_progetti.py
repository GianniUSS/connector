import json
import sys
from app import app
from flask import jsonify, request
from rentman_api import list_projects_by_date
import traceback
import requests
import config
from rentman_api import process_project, extract_id_from_path, get_all_statuses

def test_lista_progetti():
    """Testa la funzione lista_progetti con un ID progetto specificato"""
    # Permetti ID da linea di comando, default 3739
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
        try:
            project_id = int(project_id)
        except Exception:
            pass
    else:
        project_id = 3739
    print(f"🔍 TEST FUNZIONE lista_progetti con focus sul progetto {project_id}")
    
    # Simula una richiesta con date che includono sicuramente il progetto target
    test_data = {
        'fromDate': '2024-01-01',
        'toDate': '2025-12-31'
    }
    
    print(f"📅 Intervallo date di test: {test_data['fromDate']} - {test_data['toDate']}")
    
    try:
        # Ottieni progetti con list_projects_by_date
        print("⏳ Chiamata diretta a list_projects_by_date...")
        progetti = list_projects_by_date(test_data['fromDate'], test_data['toDate'])
        # Cerca per stringa o int
        target_project = None
        for p in progetti:
            if p.get('id') == project_id or p.get('id') == str(project_id) or p.get('id') == int(project_id):
                target_project = p
                break
        
        # Controlla se abbiamo trovato il progetto
        if target_project:
            print(f"\n✅ PROGETTO {project_id} TROVATO nei dati originali:")
            print(f"  - ID: {target_project.get('id')}")
            print(f"  - Nome: {target_project.get('name')}")
            print(f"  - Valore originale: {target_project.get('project_value')}")
            print(f"  - manager_name: {target_project.get('manager_name')}")
            print(f"  - manager_email: {target_project.get('manager_email')}")
            print(f"  - project_type_name: {target_project.get('project_type_name')}")
            
            # Simula la trasformazione in app.py
            transformed = {
                'id': target_project.get('id'), 
                'number': target_project.get('number'), 
                'name': target_project.get('name'), 
                'status': target_project.get('status'),
                'equipment_period_from': target_project.get('equipment_period_from'),
                'equipment_period_to': target_project.get('equipment_period_to'),
                'project_type_name': target_project.get('project_type_name'),
                'project_value': target_project.get('project_value'),
                'manager_name': target_project.get('manager_name'),
                'manager_email': target_project.get('manager_email')
            }
            
            print(f"\n🔄 TRASFORMAZIONE (simula app.py):")
            print(f"  - project_value dopo trasformazione: {transformed['project_value']}")
            print(f"  - manager_name: {transformed['manager_name']}")
            print(f"  - manager_email: {transformed['manager_email']}")
            print(f"  - project_type_name: {transformed['project_type_name']}")
            
            # Simula JSON encoding/decoding
            json_str = json.dumps({'projects': [transformed]})
            decoded = json.loads(json_str)
            
            print(f"\n🔄 DOPO JSON ENCODING/DECODING:")
            print(f"  - project_value: {decoded['projects'][0]['project_value']}")
            print(f"  - manager_name: {decoded['projects'][0]['manager_name']}")
            print(f"  - manager_email: {decoded['projects'][0]['manager_email']}")
            print(f"  - project_type_name: {decoded['projects'][0]['project_type_name']}")
            
            # Simula formattazione come nell'HTML
            html_value = f"€ {decoded['projects'][0]['project_value']}" if decoded['projects'][0]['project_value'] else 'N/A'
            print(f"\n🖥️ VISUALIZZAZIONE FINALE NELL'HTML:")
            print(f"  - Valore formattato: {html_value}")
            print(f"  - manager_name: {decoded['projects'][0]['manager_name']}")
            print(f"  - manager_email: {decoded['projects'][0]['manager_email']}")
            print(f"  - project_type_name: {decoded['projects'][0]['project_type_name']}")
            
        else:
            print(f"⚠️ PROGETTO {project_id} NON TROVATO tra i {len(progetti)} progetti recuperati")
            # Mostra i primi progetti come riferimento
            print("\nPrimi 3 progetti trovati:")
            for i, p in enumerate(progetti[:3]):
                print(f"  Progetto {i+1}: ID={p.get('id')}, NAME={p.get('name')}, VALUE={p.get('project_value')}, MANAGER={p.get('manager_name')}, EMAIL={p.get('manager_email')}, TYPE={p.get('project_type_name')}")
        
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        traceback.print_exc()

def test_process_project_direct(project_id):
    print(f"\n🔎 TEST process_project DIRETTO su progetto {project_id}")
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    # Recupera il payload grezzo
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"❌ Errore API: {response.status_code} - {response.text}")
        return
    project_data = response.json().get('data', {})
    if not project_data:
        print("❌ Nessun dato progetto trovato!")
        return
    # Simula parametri come in list_projects_by_date
    status_map = get_all_statuses(headers)
    from datetime import datetime
    start_dt = datetime.strptime('2024-01-01', "%Y-%m-%d").date()
    end_dt = datetime.strptime('2025-12-31', "%Y-%m-%d").date()
    debug_count = [0]
    processed = process_project(project_data, headers, status_map, start_dt, end_dt, debug_count)
    if not processed:
        print("❌ process_project ha restituito None (forse per date/status)")
        return
    print("\n✅ OUTPUT process_project:")
    for k in ['id','name','number','status','project_type_name','manager_name','manager_email','project_value']:
        print(f"  {k}: {processed.get(k)}")
    print("\nJSON finale:")
    print(json.dumps(processed, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_lista_progetti()
    print("\n==============================\n")
    test_process_project_direct(3739)
