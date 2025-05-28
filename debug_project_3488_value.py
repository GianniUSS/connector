import requests
import json
from datetime import datetime

# Configurazione
API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'
BASE_URL = 'https://api.rentman.net'

def extract_id_from_path(path):
    """Estrae l'ID da un path come '/projecttypes/123' """
    if not path:
        return None
    try:
        return int(path.split('/')[-1])
    except (ValueError, IndexError):
        return None

def process_project_value(project_data):
    """Simula la funzione process_project focalizzandosi solo sul valore"""
    print(f"🔍 Analisi valore progetto {project_data.get('id')} - {project_data.get('name')}")
    
    # Debug campi di valore
    print(f"💰 Tutti i campi di valore disponibili:")
    value_fields_found = False
    for key, value in project_data.items():
        if any(term in key.lower() for term in ['price', 'cost', 'total', 'value']):
            print(f"  - {key}: {value} (tipo: {type(value).__name__})")
            value_fields_found = True
    
    if not value_fields_found:
        print("  Nessun campo relativo al valore trovato")
    
    # Estrai il valore secondo la logica corrente in rentman_api.py
    print("\n🔢 SIMULAZIONE ESTRAZIONE VALORE CON LOGICA ATTUALE:")
    
    # Logica corrente (da rentman_api.py)
    project_value = project_data.get('project_total_price')
    print(f"  1. project_total_price: {project_value} (tipo: {type(project_value).__name__})")
    
    # Se project_total_price è zero o non esiste, proviamo project_total_price_cancelled
    if project_value is None or project_value == 0:
        project_value_cancelled = project_data.get('project_total_price_cancelled')
        print(f"  2. project_total_price è None o zero -> controllo project_total_price_cancelled: {project_value_cancelled}")
        if project_value_cancelled and project_value_cancelled > 0:
            project_value = project_value_cancelled
            print(f"     ✅ Usando project_total_price_cancelled: {project_value}")
    
    if project_value is None:
        print(f"  3. ⚠️ Nessun valore di progetto trovato, uso valore 0")
        project_value = 0
    
    # Formatta il valore come numero con due decimali
    try:
        formatted_value = '{:.2f}'.format(float(project_value))
        print(f"  4. ✅ Valore formattato: {formatted_value}")
    except (ValueError, TypeError):
        print(f"  4. ⚠️ Impossibile convertire il valore '{project_value}' in float. Uso '0.00'")
        formatted_value = '0.00'
    
    print(f"\n💰 RISULTATO FINALE: {formatted_value}")
      # Simulazione di come verrebbe visualizzato nell'interfaccia
    projectValue = f'€ {formatted_value}' if formatted_value else 'N/A'
    print(f"📊 VISUALIZZAZIONE NELL'INTERFACCIA: {projectValue}")
    
    return formatted_value

if __name__ == '__main__':
    print("🔍 RECUPERO DATI PER IL PROGETTO 3488...")
    
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Recupera il progetto
    url = f"{BASE_URL}/projects/3488"
    response = requests.get(url, headers=headers)
    
    if not response.ok:
        print(f"❌ ERRORE: {response.status_code} - {response.text}")
        exit(1)
    
    project_data = response.json().get('data', {})
    if not project_data:
        print("❌ ERRORE: Dati del progetto non trovati nella risposta")
        exit(1)
    
    print(f"✅ Dati recuperati per il progetto {project_data.get('id')} - {project_data.get('name')}\n")
    
    # Processa il valore del progetto
    process_project_value(project_data)
