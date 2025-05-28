import json
from app import app
from flask import jsonify, request
from rentman_api import list_projects_by_date
import traceback

def test_lista_progetti():
    """Testa la funzione lista_progetti con il progetto 3488"""
    print("🔍 TEST FUNZIONE lista_progetti con focus sul progetto 3488")
    
    # Simula una richiesta con date che includono sicuramente il progetto 3488
    test_data = {
        'fromDate': '2025-01-01',
        'toDate': '2025-12-31'
    }
    
    print(f"📅 Intervallo date di test: {test_data['fromDate']} - {test_data['toDate']}")
    
    try:
        # Ottieni progetti con list_projects_by_date
        print("⏳ Chiamata diretta a list_projects_by_date...")
        progetti = list_projects_by_date(test_data['fromDate'], test_data['toDate'])
        
        # Trova il progetto 3488
        target_project = None
        for p in progetti:
            if p.get('id') == '3618':
                target_project = p
                break
        
        if not target_project:
            # Cerca per ID numerico
            for p in progetti:
                if p.get('id') == 3618:
                    target_project = p
                    break
                    
        # Controlla se abbiamo trovato il progetto
        if target_project:
            print(f"\n✅ PROGETTO 3488 TROVATO nei dati originali:")
            print(f"  - ID: {target_project.get('id')}")
            print(f"  - Nome: {target_project.get('name')}")
            print(f"  - Valore originale: {target_project.get('project_value')}")
            
            # Simula la trasformazione in app.py
            transformed = {
                'id': target_project.get('id'), 
                'number': target_project.get('number'), 
                'name': target_project.get('name'), 
                'status': target_project.get('status'),
                'equipment_period_from': target_project.get('equipment_period_from'),
                'equipment_period_to': target_project.get('equipment_period_to'),
                'project_type_name': target_project.get('project_type_name'),
                'project_value': target_project.get('project_value')
            }
            
            print(f"\n🔄 TRASFORMAZIONE (simula app.py):")
            print(f"  - project_value dopo trasformazione: {transformed['project_value']}")
            
            # Simula JSON encoding/decoding
            json_str = json.dumps({'projects': [transformed]})
            decoded = json.loads(json_str)
            
            print(f"\n🔄 DOPO JSON ENCODING/DECODING:")
            print(f"  - project_value: {decoded['projects'][0]['project_value']}")
            
            # Simula formattazione come nell'HTML
            html_value = f"€ {decoded['projects'][0]['project_value']}" if decoded['projects'][0]['project_value'] else 'N/A'
            
            print(f"\n🖥️ VISUALIZZAZIONE FINALE NELL'HTML:")
            print(f"  - Valore formattato: {html_value}")
            
        else:
            print(f"⚠️ PROGETTO 3488 NON TROVATO tra i {len(progetti)} progetti recuperati")
            # Mostra i primi progetti come riferimento
            print("\nPrimi 3 progetti trovati:")
            for i, p in enumerate(progetti[:3]):
                print(f"  Progetto {i+1}: ID={p.get('id')}, NAME={p.get('name')}, VALUE={p.get('project_value')}")
        
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_lista_progetti()
