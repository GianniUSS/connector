import requests
import config
import json

def get_first_project_id():
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera progetti
    url = f"{config.REN_BASE_URL}/projects"
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        print(f"Errore API Rentman: {response.status_code}: {response.text}")
        return None
    
    projects = response.json().get('data', [])
    if not projects:
        print("Nessun progetto trovato")
        return None
    
    # Prendi il primo progetto
    first_project = projects[0]
    project_id = first_project.get('id')
    
    print(f"Trovato progetto con ID: {project_id}, Nome: {first_project.get('name')}")
    return project_id

def analyze_subprojects(project_id):
    if not project_id:
        return
        
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # URL dei subprojects
    url = f"{config.REN_BASE_URL}/subprojects"
    params = {'filter[project]': f'/projects/{project_id}'}
    
    # Recupera i subprojects
    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        print(f"Errore API Rentman: {response.status_code}: {response.text}")
        return
    
    # Estrai i dati dei subprojects
    subprojects = response.json().get('data', [])
    if not subprojects:
        print("Nessun subproject trovato per questo progetto")
        return
    
    print(f"Trovati {len(subprojects)} subprojects")
    
    # Analizza i subprojects
    total_value = 0
    
    for i, subproject in enumerate(subprojects):
        print(f"\n📋 SUBPROJECT {i+1}:")
        
        # Stampa campi relativi al prezzo/valore
        print("  💰 CAMPI RELATIVI AL PREZZO/VALORE:")
        price_found = False
        for key, value in subproject.items():
            if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount', 'budget']):
                print(f"    - {key}: {value}")
                price_found = True
                
                # Cerca di accumulare i valori
                if key == 'price' and value is not None:
                    try:
                        total_value += float(value)
                    except (ValueError, TypeError):
                        pass
        
        if not price_found:
            print("    Nessun campo relativo al prezzo trovato")
    
    print(f"\n💰 VALORE TOTALE CALCOLATO DAI SUBPROJECTS (campo 'price'): {total_value:.2f}")
    
    # Verifica anche il progetto principale
    main_project_url = f"{config.REN_BASE_URL}/projects/{project_id}"
    main_response = requests.get(main_project_url, headers=headers)
    
    if main_response.ok:
        main_project = main_response.json().get('data', {})
        
        print("\n📊 CONFRONTO CON IL PROGETTO PRINCIPALE:")
        for key, value in main_project.items():
            if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount', 'budget']):
                print(f"  - {key}: {value}")

if __name__ == "__main__":
    project_id = get_first_project_id()
    analyze_subprojects(project_id)
