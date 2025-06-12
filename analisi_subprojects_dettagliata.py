#!/usr/bin/env python3
"""
🔍 ANALISI DETTAGLIATA SUBPROJECTS - 9 GIUGNO 2025
Analizza la struttura dei subprojects per trovare project_total_price
"""

import sys
import os
sys.path.append(r'e:\AppConnettor')

def analyze_subprojects_structure():
    """Analizza la struttura dei subprojects in dettaglio"""
    try:
        print("🔍 ANALISI DETTAGLIATA SUBPROJECTS")
        print("="*60)
        
        import config
        import requests
        import rentman_projects
        
        # Headers per API
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        # Recupera primi progetti
        print("📊 Recupero progetti...")
        url = f"{config.REN_BASE_URL}/projects"
        response = requests.get(url, headers=headers)
        
        if not response.ok:
            print(f"❌ Errore API: {response.status_code}")
            return
            
        projects = response.json().get('data', [])[:5]  # Solo primi 5
        print(f"✅ Analizzo {len(projects)} progetti")
        
        for i, project in enumerate(projects):
            project_id = project.get('id')
            project_name = project.get('name', 'N/A')
            
            print(f"\n{'='*50}")
            print(f"🔍 PROGETTO {i+1}: {project_name} (ID: {project_id})")
            print(f"{'='*50}")
            
            # Verifica project_total_price nel progetto principale
            main_value = project.get('project_total_price')
            print(f"📄 project_total_price nel main: {main_value}")
            
            # Recupera subprojects
            subprojects = rentman_projects.get_project_subprojects_fast(project_id, headers)
            
            if subprojects:
                print(f"📊 Subprojects trovati: {len(subprojects)}")
                
                # Analizza ogni subproject
                for j, sub in enumerate(subprojects):
                    sub_id = sub.get('id')
                    sub_value = sub.get('project_total_price')
                    sub_order = sub.get('order', 'N/A')
                    sub_financial = sub.get('in_financial', False)
                    sub_name = sub.get('name', 'N/A')
                    
                    print(f"\n  📋 Subproject {j+1}: {sub_name}")
                    print(f"      ID: {sub_id}")
                    print(f"      Order: {sub_order}")
                    print(f"      In Financial: {sub_financial}")
                    print(f"      project_total_price: {sub_value}")
                    
                    if sub_value and float(sub_value) > 0:
                        print(f"      ✅ VALORE VALIDO TROVATO: {sub_value}")
                    
                    # Mostra tutti i campi numerici del subproject
                    numeric_fields = {k: v for k, v in sub.items() 
                                    if isinstance(v, (int, float)) and v > 0}
                    if numeric_fields:
                        print(f"      🔢 Campi numerici: {numeric_fields}")
                
                # Strategia di priorità
                print(f"\n  🎯 STRATEGIA PRIORITÀ:")
                financial_subs = [s for s in subprojects if s.get('in_financial') is True]
                if financial_subs:
                    print(f"      Financial subprojects: {len(financial_subs)}")
                    best_sub = min(financial_subs, key=lambda s: s.get('order', 9999))
                    best_value = best_sub.get('project_total_price')
                    print(f"      Migliore (order più basso): ID {best_sub.get('id')}, valore: {best_value}")
                else:
                    print(f"      Nessun subproject con in_financial=True")
                    if subprojects:
                        best_sub = min(subprojects, key=lambda s: s.get('order', 9999))
                        best_value = best_sub.get('project_total_price')
                        print(f"      Migliore per order: ID {best_sub.get('id')}, valore: {best_value}")
            else:
                print("📭 Nessun subproject trovato")
                
        print(f"\n{'='*60}")
        print("🎯 ANALISI COMPLETATA")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Errore durante analisi: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_subprojects_structure()
