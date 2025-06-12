#!/usr/bin/env python3
"""
🔍 ANALISI RAPIDA STRUTTURA PROGETTI
Mostra la struttura grezza dei progetti per capire dove si trova il valore
"""

import sys
import os
sys.path.append(r'e:\AppConnettor')

def quick_analysis():
    """Analisi rapida della struttura progetti"""
    try:
        print("🔍 ANALISI RAPIDA STRUTTURA PROGETTI")
        print("="*45)
        
        import config
        import requests
        
        # Headers per API
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        # Recupera primi progetti
        url = f"{config.REN_BASE_URL}/projects"
        print(f"📡 Chiamata API: {url}")
        
        response = requests.get(url, headers=headers)
        
        if not response.ok:
            print(f"❌ Errore API: {response.status_code}")
            return
        
        data = response.json()
        projects = data.get('data', [])
        
        print(f"📊 Progetti totali ricevuti: {len(projects)}")
        
        if projects:
            # Analizza primo progetto
            first_project = projects[0]
            project_id = first_project.get('id')
            
            print(f"\n🔍 PRIMO PROGETTO (ID: {project_id}):")
            print("-" * 35)
            
            # Mostra tutti i campi
            for key, value in first_project.items():
                if value is not None:
                    # Evidenzia campi che potrebbero contenere valori
                    if any(word in key.lower() for word in ['price', 'cost', 'value', 'amount', 'total']):
                        print(f"💰 {key}: {value} (tipo: {type(value)})")
                    else:
                        print(f"   {key}: {value}")
            
            # Verifica subprojects
            print(f"\n📋 SUBPROJECTS PER PROGETTO {project_id}:")
            print("-" * 35)
            
            subprojects_url = f"{config.REN_BASE_URL}/subprojects?project={project_id}"
            sub_response = requests.get(subprojects_url, headers=headers)
            
            if sub_response.ok:
                subprojects = sub_response.json().get('data', [])
                print(f"📊 Subprojects trovati: {len(subprojects)}")
                
                for i, sub in enumerate(subprojects):
                    sub_id = sub.get('id')
                    order = sub.get('order', 'N/A')
                    in_financial = sub.get('in_financial', 'N/A')
                    
                    print(f"\n  🔹 Subproject {i+1} (ID: {sub_id}, Order: {order}, Financial: {in_financial}):")
                    
                    # Mostra campi valore nel subproject
                    for key, value in sub.items():
                        if value is not None and any(word in key.lower() for word in ['price', 'cost', 'value', 'amount', 'total']):
                            print(f"    💰 {key}: {value} (tipo: {type(value)})")
            else:
                print(f"❌ Errore recuperando subprojects: {sub_response.status_code}")
        
        print("\n🎯 CERCA QUESTI PATTERN:")
        print("💰 = Campi che potrebbero contenere valori monetari")
        print("🔍 = Analizza la struttura per capire dove sono i valori")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_analysis()
