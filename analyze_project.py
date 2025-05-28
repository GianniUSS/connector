import requests
import config
import json
import sys

def get_project_full_details(project_id):
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # URL del progetto specifico
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    
    try:
        # Recupera il progetto
        response = requests.get(url, headers=headers)
        if not response.ok:
            print(f"Errore API Rentman: {response.status_code}: {response.text}")
            return None
        
        # Estrai i dati del progetto
        project = response.json().get('data', {})
        if not project:
            print(f"Progetto {project_id} non trovato")
            return None
        
        # Stampa tutti i campi del progetto
        print("\n🔍 TUTTI I CAMPI DEL PROGETTO:")
        for key, value in sorted(project.items()):
            print(f"  - {key}: {value}")
        
        # Cerca campi relativi al prezzo/valore
        print("\n💰 CAMPI RELATIVI AL PREZZO/VALORE:")
        price_fields = []
        for key, value in project.items():
            if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount', 'budget']):
                price_fields.append((key, value))
                print(f"  - {key}: {value}")
        
        # Controlla i subprojects per eventuali valori
        print("\n🔍 CONTROLLO SUBPROJECTS PER VALORI:")
        subprojects_url = f"{config.REN_BASE_URL}/subprojects"
        params = {'filter[project]': f'/projects/{project_id}'}
        
        sub_response = requests.get(subprojects_url, headers=headers, params=params)
        if sub_response.ok:
            subprojects = sub_response.json().get('data', [])
            if subprojects:
                print(f"  Trovati {len(subprojects)} subprojects")
                
                # Estrai i valori dai primi 3 subprojects
                for i, subproject in enumerate(subprojects[:3]):
                    print(f"\n  Subproject {i+1}:")
                    for key, value in subproject.items():
                        if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount', 'budget']):
                            print(f"    - {key}: {value}")
            else:
                print("  Nessun subproject trovato")
        else:
            print(f"  Errore recuperando subprojects: {sub_response.status_code}")
        
        return project
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        return None

if __name__ == "__main__":
    # Ottieni l'ID del progetto da riga di comando o richiedi input
    if len(sys.argv) > 1:
        project_id = sys.argv[1]
    else:
        project_id = input("Inserisci l'ID del progetto da analizzare: ")
    
    print(f"🔍 Analisi dettagliata del progetto {project_id}...")
    get_project_full_details(project_id)
