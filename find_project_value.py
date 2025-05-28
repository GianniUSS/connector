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

def analyze_project(project_id):
    if not project_id:
        return
        
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # URL del progetto specifico
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    
    # Recupera il progetto
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"Errore API Rentman: {response.status_code}: {response.text}")
        return
    
    # Estrai i dati del progetto
    project = response.json().get('data', {})
    
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

if __name__ == "__main__":
    project_id = get_first_project_id()
    analyze_project(project_id)
