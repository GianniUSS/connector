#!/usr/bin/env python3
"""
🔍 DIAGNOSTICO COMPLETO - 3 PROBLEMI IDENTIFICATI
1. Progetti mancanti: 3202, 3438
2. Valori N/A (tranne primo)
3. Colonna QB_IMPORT vuota
"""

import sys
import os
sys.path.append(r'e:\AppConnettor')

def diagnostico_3_problemi():
    """Analizza i 3 problemi identificati"""
    try:
        print("🔍 DIAGNOSTICO COMPLETO - 3 PROBLEMI")
        print("="*60)
        
        import rentman_projects
        import config
        import requests
        
        # Setup headers
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        test_date = "2025-06-06"
        
        print(f"🎯 Data test: {test_date}")
        print("\n" + "="*60)
        
        # PROBLEMA 1: PROGETTI MANCANTI 3202 e 3438
        print("🔍 PROBLEMA 1: RICERCA PROGETTI MANCANTI 3202 e 3438")
        print("="*60)
        
        missing_ids = [3202, 3438]
        
        for project_id in missing_ids:
            print(f"\n📋 Cercando progetto {project_id}...")
            
            # Test 1: Progetto singolo
            try:
                url = f"{config.REN_BASE_URL}/projects/{project_id}"
                response = requests.get(url, headers=headers, timeout=8)
                
                if response.ok:
                    project = response.json().get('data', {})
                    name = project.get('name', 'N/A')
                    period_start = project.get('planperiod_start')
                    period_end = project.get('planperiod_end')
                    
                    print(f"  ✅ Progetto {project_id} ESISTE:")
                    print(f"     Nome: {name}")
                    print(f"     Periodo: {period_start} → {period_end}")
                    
                    # Verifica periodo 06/06/2025
                    if period_start and period_end:
                        from datetime import datetime
                        try:
                            ps = datetime.fromisoformat(period_start[:10]).date()
                            pe = datetime.fromisoformat(period_end[:10]).date()
                            target = datetime(2025, 6, 6).date()
                            
                            in_period = ps <= target <= pe
                            print(f"     Nel periodo 06/06/2025: {'✅ SÌ' if in_period else '❌ NO'}")
                            print(f"     Start: {ps} <= {target}: {ps <= target}")
                            print(f"     End: {target} <= {pe}: {target <= pe}")
                        except Exception as e:
                            print(f"     ❌ Errore parsing periodo: {e}")
                else:
                    print(f"  ❌ Progetto {project_id} NON TROVATO: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Errore cercando progetto {project_id}: {e}")
        
        # Test 2: Verifica paginazione completa
        print(f"\n📊 VERIFICA PAGINAZIONE COMPLETA...")
        projects = rentman_projects.list_projects_by_date_unified(test_date, test_date)
        found_ids = [p.get('id') for p in projects]
        
        print(f"✅ Progetti totali trovati: {len(projects)}")
        print(f"🔍 IDs trovati: {sorted(found_ids)}")
        
        for missing_id in missing_ids:
            if missing_id in found_ids:
                print(f"✅ {missing_id}: TROVATO")
            else:
                print(f"❌ {missing_id}: MANCANTE")
        
        # PROBLEMA 2: ANALISI VALORI
        print(f"\n" + "="*60)
        print("💰 PROBLEMA 2: ANALISI VALORI")
        print("="*60)
        
        projects_with_values = []
        projects_without_values = []
        
        for i, project in enumerate(projects):
            project_id = project.get('id')
            project_value = project.get('project_value')
            project_name = project.get('name', 'N/A')[:30]
            
            print(f"\n📋 Progetto {i+1}: ID {project_id}")
            print(f"   Nome: {project_name}")
            print(f"   Valore: {project_value}")
            
            if project_value and project_value not in ['0.00', 'N/A', None]:
                projects_with_values.append(project)
                print(f"   ✅ HA VALORE")
            else:
                projects_without_values.append(project)
                print(f"   ❌ SENZA VALORE")
        
        print(f"\n📊 STATISTICHE VALORI:")
        print(f"   ✅ Con valore: {len(projects_with_values)}")
        print(f"   ❌ Senza valore: {len(projects_without_values)}")
        
        # Test valori da API singola
        if projects_without_values:
            print(f"\n🔍 TEST VALORI DA API SINGOLA (primi 3 senza valore)...")
            
            for project in projects_without_values[:3]:
                project_id = project.get('id')
                print(f"\n  🎯 Test progetto {project_id}:")
                
                try:
                    url = f"{config.REN_BASE_URL}/projects/{project_id}"
                    response = requests.get(url, headers=headers, timeout=8)
                    
                    if response.ok:
                        single_project = response.json().get('data', {})
                        single_value = single_project.get('project_total_price')
                        print(f"     API singola: project_total_price = {single_value}")
                        
                        if single_value and float(single_value) > 0:
                            print(f"     ✅ VALORE DISPONIBILE nella API singola!")
                        else:
                            print(f"     ❌ Anche API singola ha valore nullo")
                    else:
                        print(f"     ❌ Errore API singola: {response.status_code}")
                        
                except Exception as e:
                    print(f"     ❌ Errore test API singola: {e}")
        
        # PROBLEMA 3: COLONNA QB_IMPORT
        print(f"\n" + "="*60)
        print("📤 PROBLEMA 3: ANALISI COLONNA QB_IMPORT")
        print("="*60)
        
        qb_import_found = False
        
        for i, project in enumerate(projects[:5]):  # Primi 5 progetti
            project_id = project.get('id')
            project_name = project.get('name', 'N/A')[:25]
            
            # Controlla tutte le chiavi del progetto
            qb_fields = [k for k in project.keys() if 'qb' in k.lower() or 'import' in k.lower()]
            
            print(f"\n📋 Progetto {project_id} ({project_name}):")
            print(f"   Campi QB/Import trovati: {qb_fields}")
            
            # Mostra tutti i campi per debug
            all_fields = list(project.keys())
            print(f"   Tutti i campi: {all_fields}")
            
            if qb_fields:
                qb_import_found = True
                for field in qb_fields:
                    value = project.get(field)
                    print(f"   {field}: {value}")
        
        if not qb_import_found:
            print("\n❌ NESSUN CAMPO QB_IMPORT TROVATO!")
            print("💡 La colonna QB_IMPORT potrebbe non essere implementata")
        
        print(f"\n" + "="*60)
        print("🏁 DIAGNOSTICO COMPLETATO")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Errore durante diagnostico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostico_3_problemi()
