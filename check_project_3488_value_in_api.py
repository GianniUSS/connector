from rentman_api import list_projects_by_date
import json

def check_project_value_in_api():
    """Verifica il valore del progetto 3488 nell'output dell'API"""
    print("🔍 Verifica valore progetto 3488 nell'output dell'API")
    
    # Intervallo date che include sicuramente il progetto 3488
    from_date = '2025-01-01'
    to_date = '2025-12-31'
    
    print(f"📅 Intervallo date: {from_date} - {to_date}")
    
    try:
        # Ottieni tutti i progetti in questo intervallo
        print("⏳ Chiamata a list_projects_by_date...")
        progetti = list_projects_by_date(from_date, to_date)
        
        print(f"✅ Recuperati {len(progetti)} progetti")
        
        # Cerca il progetto 3488
        target_project = None
        for p in progetti:
            if str(p.get('id')) == '3488':
                target_project = p
                break
        
        if target_project:
            print(f"\n🎯 PROGETTO 3488 TROVATO:")
            print(f"  - ID: {target_project.get('id')}")
            print(f"  - Nome: {target_project.get('name')}")
            print(f"  - Numero: {target_project.get('number')}")
            print(f"  - Stato: {target_project.get('status')}")
            print(f"  - Tipo progetto: {target_project.get('project_type_name')}")
            print(f"  - Valore: {target_project.get('project_value')}")
            
            # Verifica il tipo di dati del valore
            value = target_project.get('project_value')
            print(f"\n🔍 ANALISI VALORE:")
            print(f"  - Valore grezzo: {value}")
            print(f"  - Tipo: {type(value).__name__}")
            
            # Simulazione output API (come nell'app.py)
            output = {
                'id': target_project.get('id'), 
                'number': target_project.get('number'), 
                'name': target_project.get('name'), 
                'status': target_project.get('status'),
                'equipment_period_from': target_project.get('equipment_period_from'),
                'equipment_period_to': target_project.get('equipment_period_to'),
                'project_type_name': target_project.get('project_type_name'),
                'project_value': target_project.get('project_value')
            }
            
            # Simulazione serializzazione JSON (come avviene nell'API)
            json_str = json.dumps({'projects': [output]})
            decoded = json.loads(json_str)
            
            print(f"\n🔄 DOPO SERIALIZZAZIONE JSON:")
            print(f"  - Valore: {decoded['projects'][0]['project_value']}")
            print(f"  - Tipo: {type(decoded['projects'][0]['project_value']).__name__}")
            
            # Verifica come viene visualizzato nell'HTML
            html_value = f"€ {decoded['projects'][0]['project_value']}" if decoded['projects'][0]['project_value'] else 'N/A'
            print(f"\n🖥️ VISUALIZZAZIONE NELL'HTML:")
            print(f"  - {html_value}")
            
        else:
            print(f"⚠️ PROGETTO 3488 NON TROVATO")
            # Mostra i primi progetti come riferimento
            print("\nPrimi 3 progetti per riferimento:")
            for i, p in enumerate(progetti[:3]):
                print(f"  Progetto {i+1}: ID={p.get('id')}, NAME={p.get('name')}, VALUE={p.get('project_value')}")
            
    except Exception as e:
        import traceback
        print(f"❌ ERRORE: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_project_value_in_api()
