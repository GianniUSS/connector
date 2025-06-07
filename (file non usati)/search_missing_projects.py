#!/usr/bin/env python3
"""
Script per cercare i progetti mancanti 3143 e 3322 con query diretta
"""

import requests
import config
import logging

def search_missing_projects():
    """Cerca i progetti mancanti 3143 e 3322"""
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    missing_numbers = [3143, 3322]
    
    print("🔍 RICERCA PROGETTI MANCANTI")
    print("="*50)
    
    for number in missing_numbers:
        print(f"\n📋 Cercando progetto numero {number}...")
        
        # Cerca per numero progetto
        url = f"{config.REN_BASE_URL}/projects"
        params = {'number': number}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"GET {url}?number={number} → Status: {response.status_code}")
            
            if response.ok:
                data = response.json().get('data', [])
                
                if data:
                    # Assicurati che data sia una lista
                    if isinstance(data, dict):
                        data = [data]
                    
                    for project in data:
                        project_id = project.get('id')
                        project_number = project.get('number')
                        project_name = project.get('name', 'N/A')
                        plan_start = project.get('planperiod_start', 'N/A')
                        plan_end = project.get('planperiod_end', 'N/A')
                        
                        print(f"  ✅ TROVATO!")
                        print(f"     ID: {project_id}")
                        print(f"     Number: {project_number}")
                        print(f"     Name: {project_name}")
                        print(f"     Period: {plan_start} → {plan_end}")
                        
                        # Verifica overlap con 05/06/2025
                        if plan_start and plan_end:
                            start_clean = plan_start[:10]
                            end_clean = plan_end[:10]
                            target_date = "2025-06-05"
                            
                            overlap = start_clean <= target_date <= end_clean
                            print(f"     Overlap con 05/06/2025: {'✅ SÌ' if overlap else '❌ NO'}")
                            
                            if overlap:
                                print(f"     🚨 QUESTO PROGETTO DOVREBBE ESSERE INCLUSO!")
                else:
                    print(f"  ❌ Non trovato con query number={number}")
            else:
                print(f"  ❌ Errore API: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  ❌ Errore: {e}")
    
    print("\n" + "="*50)
    print("🔍 RICERCA PROGETTI PER ID (dai mappings noti)")
    print("="*50)
    
    # IDs noti dai test precedenti
    missing_ids = [3120, 3299]  # IDs per numeri 3143 e 3322
    
    for project_id in missing_ids:
        print(f"\n📋 Cercando progetto ID {project_id}...")
        
        url = f"{config.REN_BASE_URL}/projects/{project_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"GET {url} → Status: {response.status_code}")
            
            if response.ok:
                project = response.json().get('data', {})
                
                project_number = project.get('number')
                project_name = project.get('name', 'N/A')
                plan_start = project.get('planperiod_start', 'N/A')
                plan_end = project.get('planperiod_end', 'N/A')
                
                print(f"  ✅ TROVATO!")
                print(f"     ID: {project_id}")
                print(f"     Number: {project_number}")
                print(f"     Name: {project_name}")
                print(f"     Period: {plan_start} → {plan_end}")
                
                # Verifica overlap con 05/06/2025
                if plan_start and plan_end:
                    start_clean = plan_start[:10]
                    end_clean = plan_end[:10]
                    target_date = "2025-06-05"
                    
                    overlap = start_clean <= target_date <= end_clean
                    print(f"     Overlap con 05/06/2025: {'✅ SÌ' if overlap else '❌ NO'}")
                    
                    if overlap:
                        print(f"     🚨 QUESTO PROGETTO DOVREBBE ESSERE INCLUSO!")
            else:
                print(f"  ❌ Errore API: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"  ❌ Errore: {e}")

if __name__ == "__main__":
    search_missing_projects()
