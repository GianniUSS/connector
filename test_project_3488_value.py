import requests
import json
from datetime import datetime

# Configurazione
API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'
BASE_URL = 'https://api.rentman.net'

def get_project(project_id):
    """Recupera direttamente un progetto dall'API Rentman"""
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Accept': 'application/json'
    }
    
    url = f"{BASE_URL}/projects/{project_id}"
    print(f"🔍 Chiamata API: {url}")
    
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"❌ Errore API: {response.status_code} - {response.text}")
        return None
    
    data = response.json().get('data')
    return data

def format_project_value(value):
    """Formatta il valore del progetto come nell'app"""
    if value is None:
        return "0.00"
    
    try:
        return '{:.2f}'.format(float(value))
    except (ValueError, TypeError):
        print(f"⚠️ Impossibile convertire il valore '{value}' in float")
        return "0.00"

def main():
    print("🔍 TEST VALORE PROGETTO 3488")
    
    # Recupera il progetto
    project = get_project('3488')
    if not project:
        print("❌ Progetto non trovato")
        return
    
    print("\n📝 INFORMAZIONI PROGETTO:")
    print(f"  - ID: {project.get('id')}")
    print(f"  - Nome: {project.get('name')}")
    print(f"  - Numero: {project.get('number')}")
    
    # Controlla tutti i campi relativi al valore
    print("\n💰 CAMPI DI VALORE:")
    for key, value in project.items():
        if any(term in key.lower() for term in ['price', 'cost', 'total', 'value']):
            print(f"  - {key}: {value} (tipo: {type(value).__name__})")
    
    # Estrai il valore seguendo la logica dell'app
    project_value = project.get('project_total_price')
    print(f"\n🔢 LOGICA DI ESTRAZIONE VALORE:")
    print(f"  1. project_total_price = {project_value}")
    
    # Usa project_total_price_cancelled come fallback
    if project_value is None or project_value == 0:
        project_value_cancelled = project.get('project_total_price_cancelled')
        print(f"  2. project_total_price_cancelled = {project_value_cancelled}")
        
        if project_value_cancelled and project_value_cancelled > 0:
            project_value = project_value_cancelled
            print(f"     ✅ Usando project_total_price_cancelled")
    
    # Formatta il valore
    formatted_value = format_project_value(project_value)
    print(f"\n💰 VALORE FINALE: {formatted_value}")
    
    # Mostra come verrebbe visualizzato nell'interfaccia
    display_value = f"€ {formatted_value}" if formatted_value else "N/A"
    print(f"📊 VISUALIZZAZIONE NELL'INTERFACCIA: {display_value}")
    
    # Verifica presenza di subprojects
    print("\n🔍 VERIFICA SUBPROJECTS:")
    url = f"{BASE_URL}/subprojects/{project.get('id')}"
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.ok:
        subprojects = response.json().get('data', [])
        if isinstance(subprojects, dict):  # API può restituire un dict per un singolo subproject
            subprojects = [subprojects]
            
        print(f"  ✅ Trovati {len(subprojects)} subprojects")
        
        # Stampa i primi subprojects
        for i, sub in enumerate(subprojects[:3]):
            print(f"\n  📄 Subproject {i+1}:")
            print(f"    - ID: {sub.get('id')}")
            print(f"    - Nome: {sub.get('name')}")
            
            # Controlla se c'è un campo di stato
            status_path = sub.get('status')
            if status_path:
                print(f"    - Status path: {status_path}")
    else:
        print(f"  ❌ Errore recuperando subprojects: {response.status_code}")

if __name__ == "__main__":
    main()
