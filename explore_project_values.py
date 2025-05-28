import requests
import config
import json
import sys

def get_projects_with_values():
    """Recupera alcuni progetti e mostra tutti i valori disponibili"""
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera progetti
    url = f"{config.REN_BASE_URL}/projects"
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        print(f"Errore API Rentman: {response.status_code}: {response.text}")
        return
    
    projects = response.json().get('data', [])
    
    if not projects:
        print("Nessun progetto trovato")
        return
    
    print(f"Trovati {len(projects)} progetti")
    
    # Analizza i primi 5 progetti
    for i, project in enumerate(projects[:5]):
        if i > 0:
            print("\n" + "="*80 + "\n")  # Separatore
            
        print(f"PROGETTO {i+1}:")
        print(f"  ID: {project.get('id')}")
        print(f"  Nome: {project.get('name')}")
        
        # Controlla tutti i campi disponibili
        print(f"\nCAMPI DISPONIBILI NEL PROGETTO:")
        
        # Mostra tutti i campi relativi a costi, prezzi, valori
        value_fields = {}
        for key, value in project.items():
            if any(term in key.lower() for term in ['price', 'value', 'total', 'cost', 'amount', 'budget']):
                value_fields[key] = value
                
        # Stampa tutti i campi relativi ai valori
        if value_fields:
            print("  CAMPI RELATIVI AI VALORI:")
            for key, value in sorted(value_fields.items()):
                print(f"    - {key}: {value}")
        else:
            print("  Nessun campo relativo a valori trovato")
        
        # Mostra il campo price specifico se esiste
        price = project.get('price')
        if price is not None:
            print(f"\n  Campo 'price': {price}")
        else:
            print(f"\n  Campo 'price' non trovato")
            
        # Mostra struttura dati completa
        print(f"\nSTRUTTURA DATI COMPLETA:")
        print(json.dumps(project, indent=2))

if __name__ == "__main__":
    print("Analisi dei progetti Rentman e dei loro valori...")
    get_projects_with_values()
