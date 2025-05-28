import requests
import config
import json

# Funzione per stampare il payload completo di un progetto
def get_project_details(project_id):
    print(f"📊 Recupero dettagli completi del progetto {project_id}...")
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera il progetto
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    
    try:
        response = requests.get(url, headers=headers)
        if not response.ok:
            print(f"Errore API Rentman: {response.status_code}: {response.text}")
            return
        
        project = response.json().get('data', {})
        if not project:
            print(f"Progetto {project_id} non trovato")
            return
        
        print("\n🔍 PAYLOAD COMPLETO DEL PROGETTO:")
        print(json.dumps(project, indent=2))
        
        # Cerca campi che potrebbero contenere il valore del progetto
        print("\n💰 CAMPI RELATIVI AL VALORE DEL PROGETTO:")
        for key, value in project.items():
            if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount']):
                print(f"  - {key}: {value}")
        
        # Controlla se esistono campi specifici che stiamo cercando
        print("\n🔍 VERIFICA CAMPI SPECIFICI:")
        fields_to_check = ['project_total_price', 'total_price', 'price', 'total', 'value', 'cost']
        for field in fields_to_check:
            print(f"  - {field}: {project.get(field)}")
            
        return project
    except Exception as e:
        print(f"❌ Errore: {e}")
        return None

if __name__ == "__main__":
    # Chiedi all'utente l'ID del progetto
    project_id = input("Inserisci l'ID del progetto da analizzare: ")
    get_project_details(project_id)
