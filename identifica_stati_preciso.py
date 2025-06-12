#!/usr/bin/env python3
"""
Identifica gli stati precisi dei progetti mancanti per il 06/06/2025
- AppConnector mostra 6 progetti 
- Rentman ne ha 9
- Dobbiamo trovare i 3 mancanti e i loro stati
"""

import requests
from datetime import datetime
import json

def get_all_projects_for_date():
    """Recupera TUTTI i progetti per il 06/06/2025 senza filtri di stato"""
    try:
        url = "https://api.rentman.io/projects"
        headers = {
            'Authorization': 'Bearer 1b34f6fd-ff03-4859-ab23-7d88af7b9a53',
            'Accept': 'application/json'
        }
        
        # Data target: 06/06/2025
        target_date = "2025-06-06"
        
        params = {
            'planperiod_start[gte]': target_date,
            'planperiod_end[lte]': target_date,
            'offset': 0,
            'limit': 100
        }
        
        print(f"🔄 Recuperando TUTTI i progetti per {target_date}...")
        print(f"📡 URL: {url}")
        print(f"📋 Parametri: {params}")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            print(f"✅ Trovati {len(projects)} progetti totali")
            return projects
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"   Risposta: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Errore: {e}")
        return []

def get_appconnector_filtered_projects():
    """Recupera progetti usando i filtri dell'AppConnector"""
    try:
        url = "https://api.rentman.io/projects"
        headers = {
            'Authorization': 'Bearer 1b34f6fd-ff03-4859-ab23-7d88af7b9a53',
            'Accept': 'application/json'
        }
        
        # Data target: 06/06/2025
        target_date = "2025-06-06"
        
        # Stati validi dall'AppConnector
        valid_states = [
            'Confirmed', 'Confermato', 'Request', 'Richiesta', 
            'Option', 'Opzione', 'Prep', 'Preparazione', 
            'Out', 'Fuori', 'Returned', 'Rientrato'
        ]
        
        params = {
            'planperiod_start[gte]': target_date,
            'planperiod_end[lte]': target_date,
            'status[in]': ','.join(valid_states),
            'offset': 0,
            'limit': 100
        }
        
        print(f"🔄 Recuperando progetti con filtri AppConnector...")
        print(f"📋 Stati filtrati: {valid_states}")
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            projects = data.get('data', [])
            print(f"✅ Trovati {len(projects)} progetti filtrati")
            return projects
        else:
            print(f"❌ Errore API: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Errore: {e}")
        return []

def analyze_differences():
    """Analizza le differenze tra tutti i progetti e quelli filtrati"""
    print("🎯 ANALISI STATI PROGETTI MANCANTI")
    print("=" * 50)
    
    # Recupera entrambi i set
    all_projects = get_all_projects_for_date()
    filtered_projects = get_appconnector_filtered_projects()
    
    if not all_projects:
        print("❌ Nessun progetto recuperato!")
        return
    
    print(f"\n📊 RISULTATI:")
    print(f"   Tutti i progetti: {len(all_projects)}")
    print(f"   Progetti filtrati: {len(filtered_projects)}")
    print(f"   Progetti mancanti: {len(all_projects) - len(filtered_projects)}")
    
    # Crea set di ID per confronto
    all_ids = set(p['id'] for p in all_projects)
    filtered_ids = set(p['id'] for p in filtered_projects)
    missing_ids = all_ids - filtered_ids
    
    print(f"\n📋 DETTAGLI PROGETTI:")
    print(f"   IDs tutti: {sorted(all_ids)}")
    print(f"   IDs filtrati: {sorted(filtered_ids)}")
    print(f"   IDs mancanti: {sorted(missing_ids)}")
    
    # Analizza tutti gli stati presenti
    all_states = {}
    for project in all_projects:
        status = project.get('status', 'N/A')
        if status not in all_states:
            all_states[status] = []
        all_states[status].append(project['id'])
    
    print(f"\n🏷️  STATI PRESENTI:")
    for status, project_ids in sorted(all_states.items()):
        count = len(project_ids)
        is_filtered = status in ['Confirmed', 'Confermato', 'Request', 'Richiesta', 
                                'Option', 'Opzione', 'Prep', 'Preparazione', 
                                'Out', 'Fuori', 'Returned', 'Rientrato']
        filter_status = "✅ INCLUSO" if is_filtered else "❌ ESCLUSO"
        print(f"   {status}: {count} progetti {filter_status}")
        if project_ids:
            print(f"      IDs: {sorted(project_ids)}")
    
    # Dettagli sui progetti mancanti
    if missing_ids:
        print(f"\n🔍 DETTAGLI PROGETTI MANCANTI:")
        for project in all_projects:
            if project['id'] in missing_ids:
                status = project.get('status', 'N/A')
                name = project.get('name', 'N/A')
                print(f"   ID {project['id']}: '{name}' - Stato: '{status}'")
    
    return all_projects, filtered_projects, missing_ids

if __name__ == "__main__":
    analyze_differences()
