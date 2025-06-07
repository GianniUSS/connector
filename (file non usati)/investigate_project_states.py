#!/usr/bin/env python3
"""
Script per identificare gli stati esatti dei progetti target mancanti
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rentman_api_fast_v2 import RentmanFastAPI
import config
import logging

def investigate_missing_projects_states():
    """Identifica gli stati dei progetti target che vengono esclusi"""
    
    # Numeri progetto da Rentman
    target_numbers = [3143, 3322, 3560, 3637, 3705, 3766, 3781, 3795, 3803]
    
    print("="*70)
    print("INVESTIGAZIONE STATI PROGETTI MANCANTI")
    print("="*70)
    
    # Inizializza API
    api = RentmanFastAPI(config.REN_API_TOKEN)
    
    # Recupera TUTTI i progetti (prima del filtro stati)
    print("📡 Recupero progetti dal 05/06/2025 PRIMA del filtro stati...")
    from_date = "2025-06-05"
    to_date = "2025-06-05"
    
    # Uso il metodo interno per ottenere progetti DOPO filtro date MA prima filtro stati
    all_projects = api._fetch_all_projects_simple()
    print(f"Progetti totali dall'API: {len(all_projects)}")
    
    # Applico SOLO filtro date (come fa la modalità normale)
    start_dt = api._parse_date(from_date)
    end_dt = api._parse_date(to_date)
    
    date_filtered = []
    for project in all_projects:
        plan_start = project.get('planperiod_start', '')
        plan_end = project.get('planperiod_end', '')
        
        if plan_start and plan_end:
            start_clean = plan_start[:10]
            end_clean = plan_end[:10]
            if start_clean <= to_date and end_clean >= from_date:
                date_filtered.append(project)
    
    print(f"Progetti dopo filtro DATE: {len(date_filtered)}")
    
    # Arricchimento per ottenere stati reali
    print("🔄 Arricchimento per stati reali...")
    project_ids = [p.get('id') for p in date_filtered]
    subprojects_map = api._get_subprojects_batch(project_ids)
    
    enriched_projects = []
    for p in date_filtered:
        enriched = api._enrich_project_data_oas(p, subprojects_map)
        if enriched:
            enriched_projects.append(enriched)
    
    print(f"Progetti arricchiti: {len(enriched_projects)}")
    print()
    
    # Trova i progetti target e i loro stati
    print("🎯 RICERCA PROGETTI TARGET:")
    print("-" * 50)
    
    found_targets = []
    all_states = set()
    
    for p in enriched_projects:
        number = p.get('number')
        status = p.get('status', 'N/A')
        all_states.add(status)
        
        if number in target_numbers:
            found_targets.append({
                'number': number,
                'id': p.get('id'),
                'status': status,
                'name': p.get('name', '')
            })
    
    found_targets.sort(key=lambda x: x['number'])
    
    print(f"Progetti target trovati: {len(found_targets)}/{len(target_numbers)}")
    print()
    
    # Mostra stati dei target trovati
    for target in found_targets:
        print(f"Progetto {target['number']} (ID {target['id']}): '{target['status']}'")
        print(f"  Nome: {target['name']}")
        print()
    
    # Progetti target mancanti
    found_numbers = [t['number'] for t in found_targets]
    missing_numbers = [n for n in target_numbers if n not in found_numbers]
    
    if missing_numbers:
        print(f"❌ Progetti target COMPLETAMENTE MANCANTI: {missing_numbers}")
        print("   (Non superano nemmeno il filtro date)")
        print()
    
    # Analisi stati
    print("📊 TUTTI GLI STATI PRESENTI NEL PERIODO:")
    print("-" * 50)
    states_count = {}
    for p in enriched_projects:
        status = p.get('status', 'N/A')
        if status not in states_count:
            states_count[status] = 0
        states_count[status] += 1
    
    for status, count in sorted(states_count.items()):
        print(f"  '{status}': {count} progetti")
    
    print()
    
    # Confronto con filtro attuale
    stati_validi_attuali = {'confermato', 'rientrato', 'in location', 'pronto', 'confirmed', 'returned', 'on location', 'ready'}
    
    print("🔍 ANALISI FILTRO STATI ATTUALE:")
    print("-" * 50)
    
    target_states = set(t['status'] for t in found_targets)
    
    for status in sorted(target_states):
        status_lower = status.lower().strip()
        is_valid = status_lower in stati_validi_attuali
        validity = "✅ PASSA FILTRO" if is_valid else "❌ ESCLUSO"
        
        target_count = len([t for t in found_targets if t['status'] == status])
        print(f"  '{status}' → {validity} ({target_count} progetti target)")
    
    print()
    
    # Calcola impatto
    excluded_targets = [t for t in found_targets if t['status'].lower().strip() not in stati_validi_attuali]
    
    print("💡 SOLUZIONE PROPOSTA:")
    print("-" * 50)
    
    if excluded_targets:
        excluded_states = set(t['status'] for t in excluded_targets)
        print(f"Per includere tutti i progetti target, aggiungi questi stati al filtro:")
        for status in sorted(excluded_states):
            status_lower = status.lower().strip()
            count = len([t for t in excluded_targets if t['status'] == status])
            print(f"  '{status_lower}' (includerebbe {count} progetti target)")
        
        print()
        print("Stati validi aggiornati dovrebbero essere:")
        new_states = stati_validi_attuali.union(s.lower().strip() for s in excluded_states)
        print(f"  {sorted(new_states)}")
    else:
        print("✅ Tutti i progetti target trovati passano già il filtro stati!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Riduci verbosità
    investigate_missing_projects_states()
