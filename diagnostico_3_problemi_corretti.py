#!/usr/bin/env python3
"""
🔍 DIAGNOSTICO 3 PROBLEMI - IDs corretti: 3120, 3205, 3438
1. Progetto 3438 mancante
2. Valori tutti N/A tranne il primo  
3. Colonna QB_IMPORT mancante
"""

import sys
import os
sys.path.append(r'e:\AppConnettor')

def diagnostico_3_problemi():
    """Analizza i 3 problemi con gli IDs corretti"""
    try:
        print("🔍 DIAGNOSTICO 3 PROBLEMI")
        print("="*60)
        
        import rentman_projects
        import config
        import requests
        
        # Setup headers per API diretta
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        # IDs target corretti
        target_ids = [3120, 3205, 3438]
        print(f"🎯 IDs target: {target_ids}")
        
        # Test data critica
        test_date = "2025-06-06"
        print(f"📅 Data test: {test_date}")
        
        # Attiva debug
        os.environ['RENTMAN_LOG_LEVEL'] = 'DEBUG'
        
        print("\n" + "="*60)
        print("1. TEST FUNZIONE CORRENTE")
        print("="*60)
        
        projects = rentman_projects.list_projects_by_date_unified(test_date, test_date)
        print(f"📊 Progetti recuperati: {len(projects)}")
        
        # Verifica presenza target IDs
        found_ids = []
        missing_ids = []
        
        for project in projects:
            project_id = project.get('id')
            if project_id in target_ids:
                found_ids.append(project_id)
        
        for target_id in target_ids:
            if target_id not in found_ids:
                missing_ids.append(target_id)
        
        print(f"✅ IDs trovati: {found_ids}")
        print(f"❌ IDs mancanti: {missing_ids}")
        
        print("\n" + "="*60)
        print("2. ANALISI VALORI E STRUTTURA DATI")
        print("="*60)
        
        if projects:
            # Prendi il primo progetto per analizzare struttura
            first_project = projects[0]
            print(f"📋 Struttura primo progetto (ID {first_project.get('id')}):")
            
            # Campi principali
            key_fields = ['id', 'name', 'project_value', 'contact_displayname', 'QB_IMPORT']
            for field in key_fields:
                value = first_project.get(field, '*** CAMPO MANCANTE ***')
                print(f"   {field}: {value}")
            
            print(f"\n📋 Tutti i campi disponibili:")
            for field in sorted(first_project.keys()):
                print(f"   {field}")
            
            # Analisi valori per tutti i progetti
            projects_with_value = 0
            projects_without_value = 0
            
            for project in projects:
                project_value = project.get('project_value', 'N/A')
                if project_value and project_value != 'N/A' and project_value != '0.00':
                    projects_with_value += 1
                else:
                    projects_without_value += 1
            
            print(f"\n💰 ANALISI VALORI:")
            print(f"   ✅ Con valore: {projects_with_value}")
            print(f"   ❌ Senza valore: {projects_without_value}")
        
        print("\n" + "="*60)
        print("3. VERIFICA DIRETTA API PER IDs MANCANTI")
        print("="*60)
        
        for missing_id in missing_ids:
            print(f"\n🔍 Verifica diretta progetto {missing_id}:")
            
            try:
                # Test API diretta
                url = f"{config.REN_BASE_URL}/projects/{missing_id}"
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.ok:
                    project_data = response.json().get('data', {})
                    project_name = project_data.get('name', 'N/A')
                    period_start = project_data.get('planperiod_start')
                    period_end = project_data.get('planperiod_end')
                    status = project_data.get('status')
                    
                    print(f"   ✅ TROVATO in API singola:")
                    print(f"   📝 Nome: {project_name}")
                    print(f"   📅 Periodo: {period_start} → {period_end}")
                    print(f"   📊 Status: {status}")
                    
                    # Verifica se periodo include 06/06/2025
                    from datetime import datetime
                    target_date = datetime(2025, 6, 6).date()
                    
                    if period_start and period_end:
                        try:
                            ps = datetime.fromisoformat(period_start[:10]).date()
                            pe = datetime.fromisoformat(period_end[:10]).date()
                            in_period = ps <= target_date <= pe
                            print(f"   📅 Include 06/06/2025: {'✅ SÌ' if in_period else '❌ NO'}")
                            print(f"      {ps} <= {target_date} <= {pe}")
                        except:
                            print(f"   📅 Errore parsing periodo")
                    else:
                        print(f"   📅 Periodo None - dovrebbe essere incluso per ID target")
                
                else:
                    print(f"   ❌ ERRORE API: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ ERRORE: {e}")
        
        print("\n" + "="*60)
        print("4. VERIFICA RECUPERO VALORI PROGETTI TARGET")
        print("="*60)
        
        for target_id in target_ids:
            print(f"\n💰 Test valore progetto {target_id}:")
            
            try:
                url = f"{config.REN_BASE_URL}/projects/{target_id}"
                response = requests.get(url, headers=headers, timeout=5)
                
                if response.ok:
                    project_data = response.json().get('data', {})
                    project_total_price = project_data.get('project_total_price')
                    print(f"   📊 project_total_price: {project_total_price}")
                    
                    if project_total_price is None:
                        print(f"   ⚠️ Valore None - necessario recupero da subprojects")
                    elif project_total_price == 0:
                        print(f"   ⚠️ Valore zero")
                    else:
                        print(f"   ✅ Valore trovato: {project_total_price}")
                else:
                    print(f"   ❌ Errore API: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Errore: {e}")
        
        print("\n🎉 Diagnostico completato!")
        
    except Exception as e:
        print(f"❌ Errore durante diagnostico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostico_3_problemi()
