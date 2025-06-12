#!/usr/bin/env python3
"""
🔍 CONVERSIONE STATUS ID: Converte /statuses/X nei nomi reali
"""

import requests
import config

def converti_status_ids():
    """Converte gli ID status nei nomi reali"""
    
    print("🔍 CONVERSIONE STATUS ID NEI NOMI REALI")
    print("=" * 50)
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Stati trovati nei sottoprogetti financial
    status_ids_trovati = ['/statuses/2', '/statuses/5', '/statuses/6']
    
    print("📋 STATI TROVATI NEI SOTTOPROGETTI FINANCIAL:")
    print("-" * 40)
    
    for status_path in status_ids_trovati:
        try:
            # Estrai ID dal path
            status_id = status_path.split('/')[-1]
            
            # Recupera dettagli stato
            url = f"{config.REN_BASE_URL}/statuses/{status_id}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                status_data = response.json().get('data', {})
                status_name = status_data.get('name', 'Unknown')
                
                print(f"   {status_path} → '{status_name}'")
                
                # Verifica se è uno stato valido per il filtro
                stati_validi = {
                    'confermato', 'confirmed',
                    'in location', 'on location', 
                    'rientrato', 'returned'
                }
                
                status_lower = status_name.lower().strip()
                is_valid = status_lower in stati_validi
                
                if is_valid:
                    print(f"      ✅ STATO VALIDO per il filtro!")
                else:
                    print(f"      ❌ STATO NON VALIDO: '{status_name}' non è negli stati accettati")
                    print(f"      📋 Stati validi: {sorted(stati_validi)}")
            else:
                print(f"   {status_path} → ❌ Errore HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   {status_path} → ❌ Errore: {e}")
    
    print(f"\n🎯 STATO PROGETTI NEL GRID ATTUALE:")
    print("-" * 40)
    
    # Controllo stati attuali nel grid per confronto
    try:
        grid_url = "http://localhost:5000/lista-progetti"
        grid_payload = {"fromDate": "2025-06-06", "toDate": "2025-06-06"}
        
        grid_response = requests.post(grid_url, json=grid_payload, timeout=30)
        if grid_response.ok:
            grid_data = grid_response.json()
            projects = grid_data.get('projects', [])
            
            target_ids = [3120, 3205, 3438]
            for target_id in target_ids:
                target_project = next((p for p in projects if p.get('id') == target_id), None)
                if target_project:
                    current_status = target_project.get('status', 'N/A')
                    print(f"   Progetto {target_id}: Grid mostra '{current_status}'")
                else:
                    print(f"   Progetto {target_id}: NON TROVATO nel grid")
        else:
            print(f"   ❌ Errore chiamata grid: {grid_response.status_code}")
    except Exception as e:
        print(f"   ❌ Errore controllo grid: {e}")
    
    print(f"\n🔧 PROSSIMI PASSI:")
    print(f"   1. Aggiornare funzione get_project_status_unified()")
    print(f"   2. Usare 'in_financial=True' invece di 'financial=True'")
    print(f"   3. Testare che gli stati corretti vengano mostrati nel grid")

if __name__ == "__main__":
    converti_status_ids()
