#!/usr/bin/env python3
"""
Investigazione progetti mancanti 3143 e 3322 da Rentman
per il periodo 05/06/2025
"""

import requests
import json
from datetime import datetime
from config import REN_API_TOKEN

def search_project_by_number(project_number: int):
    """Cerca un progetto specifico per numero"""
    print(f"\n🔍 Ricerca progetto numero {project_number}...")
    
    # Cerca nei progetti recenti
    base_url = "https://api.rentman.net"
    headers = {
        'Authorization': f'Bearer {REN_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Prima prova: ricerca per numero
    try:
        response = requests.get(
            f"{base_url}/projects",
            headers=headers,
            params={
                'number': project_number,
                'limit': 10
            }
        )
        
        if response.status_code == 200:
            projects = response.json().get('data', [])
            print(f"   📊 Trovati {len(projects)} progetti con numero {project_number}")
            
            for project in projects:
                print(f"   📋 ID: {project.get('id')}")
                print(f"   📝 Numero: {project.get('number')}")
                print(f"   📄 Nome: {project.get('name', '')[:50]}...")
                print(f"   📊 Status: {project.get('status')}")
                print(f"   📅 Created: {project.get('created')}")
                print(f"   📅 Modified: {project.get('modified')}")
                
                # Verifica periodo
                if 'planperiod_start' in project:
                    print(f"   🗓️ Plan period: {project.get('planperiod_start')} → {project.get('planperiod_end')}")
                
                # Verifica equipment period  
                if 'equipment_period_from' in project:
                    print(f"   🛠️ Equipment period: {project.get('equipment_period_from')} → {project.get('equipment_period_to')}")
                    
                print("   " + "-" * 50)
                
            return projects
        else:
            print(f"   ❌ Errore ricerca: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Eccezione: {e}")
        
    return []

def search_all_projects_june():
    """Cerca tutti i progetti per giugno 2025"""
    print(f"\n🔍 Ricerca TUTTI i progetti per giugno 2025...")
    
    base_url = "https://api.rentman.net"
    headers = {
        'Authorization': f'Bearer {REN_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            f"{base_url}/projects",
            headers=headers,
            params={
                'planperiod_start': '2025-06-01',
                'planperiod_end': '2025-06-30',
                'limit': 50
            }
        )
        
        if response.status_code == 200:
            projects = response.json().get('data', [])
            print(f"   📊 Trovati {len(projects)} progetti per giugno 2025")
            
            target_numbers = [3143, 3322]
            found_targets = []
            
            for project in projects:
                number = project.get('number')
                try:
                    if isinstance(number, str) and number.isdigit():
                        number = int(number)
                    elif isinstance(number, (int, float)):
                        number = int(number)
                        
                    if number in target_numbers:
                        found_targets.append(project)
                        print(f"   🎯 TROVATO TARGET! ID: {project.get('id')}, Numero: {number}")
                        print(f"      📄 Nome: {project.get('name', '')[:50]}...")
                        print(f"      📊 Status: {project.get('status')}")
                        print(f"      🗓️ Plan: {project.get('planperiod_start')} → {project.get('planperiod_end')}")
                        print(f"      🛠️ Equipment: {project.get('equipment_period_from')} → {project.get('equipment_period_to')}")
                        print("      " + "-" * 40)
                        
                except (ValueError, TypeError):
                    continue
                    
            print(f"\n🎯 Target trovati: {len(found_targets)}/{len(target_numbers)}")
            for num in target_numbers:
                found = any(p.get('number') == num or (isinstance(p.get('number'), str) and p.get('number').isdigit() and int(p.get('number')) == num) for p in found_targets)
                print(f"   {'✅' if found else '❌'} Progetto {num}: {'TROVATO' if found else 'NON TROVATO'}")
                
            return projects, found_targets
        else:
            print(f"   ❌ Errore ricerca: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Eccezione: {e}")
        
    return [], []

def check_date_overlap(project, target_date):
    """Verifica se un progetto ha overlap con la data target"""
    target_dt = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    # Controlla plan period
    plan_start = project.get('planperiod_start')
    plan_end = project.get('planperiod_end')
    
    plan_overlap = False
    if plan_start and plan_end:
        try:
            plan_start_dt = datetime.strptime(plan_start, '%Y-%m-%d').date()
            plan_end_dt = datetime.strptime(plan_end, '%Y-%m-%d').date()
            plan_overlap = plan_start_dt <= target_dt <= plan_end_dt
        except:
            pass
    
    # Controlla equipment period
    equip_start = project.get('equipment_period_from')
    equip_end = project.get('equipment_period_to')
    
    equip_overlap = False
    if equip_start and equip_end:
        try:
            equip_start_dt = datetime.strptime(equip_start, '%Y-%m-%d').date()
            equip_end_dt = datetime.strptime(equip_end, '%Y-%m-%d').date()
            equip_overlap = equip_start_dt <= target_dt <= equip_end_dt
        except:
            pass
    
    return plan_overlap, equip_overlap

def main():
    """Investigazione progetti mancanti"""
    target_date = "2025-06-05"
    missing_numbers = [3143, 3322]
    
    print("=" * 80)
    print("🕵️ INVESTIGAZIONE PROGETTI MANCANTI")
    print(f"📅 Data target: {target_date}")
    print(f"🎯 Progetti mancanti: {missing_numbers}")
    print("=" * 80)
    
    # 1. Ricerca per numero specifico
    all_found_projects = []
    for number in missing_numbers:
        projects = search_project_by_number(number)
        all_found_projects.extend(projects)
    
    # 2. Ricerca generale per giugno
    june_projects, found_targets = search_all_projects_june()
    
    # 3. Analisi date overlap per progetti trovati
    if all_found_projects or found_targets:
        print(f"\n📊 ANALISI DATE OVERLAP PER {target_date}:")
        print("=" * 60)
        
        all_relevant = all_found_projects + found_targets
        unique_projects = {}
        for p in all_relevant:
            unique_projects[p.get('id')] = p
            
        for project in unique_projects.values():
            plan_overlap, equip_overlap = check_date_overlap(project, target_date)
            
            print(f"\n📋 Progetto ID {project.get('id')} - Numero {project.get('number')}")
            print(f"   📄 Nome: {project.get('name', '')[:50]}...")
            print(f"   📊 Status: {project.get('status')}")
            print(f"   🗓️ Plan period: {project.get('planperiod_start')} → {project.get('planperiod_end')}")
            print(f"   🛠️ Equipment period: {project.get('equipment_period_from')} → {project.get('equipment_period_to')}")
            print(f"   🎯 Plan overlap con {target_date}: {'✅ SÌ' if plan_overlap else '❌ NO'}")
            print(f"   🎯 Equipment overlap con {target_date}: {'✅ SÌ' if equip_overlap else '❌ NO'}")
            
            if not plan_overlap and not equip_overlap:
                print(f"   ⚠️ MOTIVO ESCLUSIONE: Nessun overlap con {target_date}")
            elif project.get('status') not in ['Confermato', 'Rientrato', 'In location', 'Pronto']:
                print(f"   ⚠️ MOTIVO ESCLUSIONE: Status '{project.get('status')}' non valido")
            else:
                print(f"   🤔 DOVREBBE ESSERE INCLUSO!")
    
    else:
        print(f"\n❌ NESSUN PROGETTO TROVATO con numeri {missing_numbers}")
        print("   Possibili cause:")
        print("   - I progetti non esistono")
        print("   - I numeri sono diversi da quelli attesi")
        print("   - I progetti sono stati eliminati")
        print("   - Problema con i filtri API")

if __name__ == "__main__":
    main()
