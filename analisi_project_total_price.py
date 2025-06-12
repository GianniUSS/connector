#!/usr/bin/env python3
"""
🔍 ANALISI DIRETTA CAMPO PROJECT_TOTAL_PRICE
Esamina i dati grezzi dell'API per capire la struttura del campo valore
"""

import sys
import os
import requests
import json
sys.path.append(r'e:\AppConnettor')

def analyze_project_total_price():
    """Analizza direttamente la struttura del campo project_total_price"""
    try:
        print("🔍 ANALISI DIRETTA CAMPO PROJECT_TOTAL_PRICE")
        print("="*60)
        
        # Import config
        import config
        
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        # 1. Test chiamata progetti con fields selection
        print("📊 Test 1: Progetti con fields selection...")
        url = f"{config.REN_BASE_URL}/projects"
        
        # Usa fields selection come suggerito nella documentazione OAS
        params = {
            'fields': 'id,name,number,project_total_price,planperiod_start,planperiod_end',
            'limit': 5  # Solo primi 5 per test
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.ok:
            data = response.json().get('data', [])
            print(f"✅ Progetti recuperati: {len(data)}")
            
            if data:
                print("\n🔍 ANALISI PRIMI PROGETTI:")
                for i, project in enumerate(data[:3]):
                    project_id = project.get('id')
                    project_name = project.get('name', 'N/A')
                    project_total_price = project.get('project_total_price')
                    
                    print(f"\n📄 Progetto {i+1}:")
                    print(f"  ID: {project_id}")
                    print(f"  Nome: {project_name}")
                    print(f"  project_total_price: {project_total_price} (tipo: {type(project_total_price)})")
                    
                    # Mostra tutti i campi disponibili
                    print(f"  📋 Tutti i campi: {list(project.keys())}")
                    
                    # Se project_total_price è presente e non nullo
                    if project_total_price is not None:
                        try:
                            float_value = float(project_total_price)
                            print(f"  ✅ Valore convertito: {float_value:.2f}")
                        except:
                            print(f"  ❌ Impossibile convertire '{project_total_price}' in numero")
                    else:
                        print(f"  ⚠️  project_total_price è None o mancante")
            
            # 2. Test subprojects per lo stesso progetto
            if data:
                test_project_id = data[0].get('id')
                print(f"\n📊 Test 2: Subprojects per progetto {test_project_id}...")
                
                subprojects_url = f"{config.REN_BASE_URL}/subprojects"
                sub_params = {
                    'project': test_project_id,
                    'fields': 'id,project_total_price,in_financial,order'
                }
                
                sub_response = requests.get(subprojects_url, headers=headers, params=sub_params, timeout=10)
                
                if sub_response.ok:
                    sub_data = sub_response.json().get('data', [])
                    print(f"✅ Subprojects trovati: {len(sub_data)}")
                    
                    if sub_data:
                        print("\n🔍 ANALISI SUBPROJECTS:")
                        for sub in sub_data:
                            sub_id = sub.get('id')
                            sub_price = sub.get('project_total_price')
                            in_financial = sub.get('in_financial')
                            order = sub.get('order')
                            
                            print(f"  📄 Subproject {sub_id}:")
                            print(f"    project_total_price: {sub_price}")
                            print(f"    in_financial: {in_financial}")
                            print(f"    order: {order}")
                    else:
                        print("  ⚠️  Nessun subproject trovato")
                else:
                    print(f"  ❌ Errore subprojects: {sub_response.status_code}")
        else:
            print(f"❌ Errore API: {response.status_code} - {response.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante analisi: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    analyze_project_total_price()
