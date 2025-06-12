#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script ottimizzato per recupero progetti Rentman (solo metodo paginato)
======================================================================
Questa versione utilizza solo il metodo paginato per il recupero dei progetti,
garantendo maggiore robustezza con dataset di grandi dimensioni, e applica gli stessi
filtri della grid web dell'applicazione Flask.

Utilizzo:
  python optimized_rentman_script.py [--verbose] [--data YYYY-MM-DD]

Opzioni:
  --verbose    Mostra informazioni dettagliate su ogni progetto
  --data       Specifica la data nel formato YYYY-MM-DD (default: 2025-06-06)

Output:
  La lista dei progetti filtrati per gli stati di interesse:
  - In location
  - Rientrato
  - Confermato
  - Pronto
"""

import sys
import time
import argparse
from datetime import datetime
from rentman_projects_fixed_clean import (
    list_projects_by_date_paginated_full_unified,
    filter_projects_by_status,
    clear_cache
)

# Configurazione
STATI_INTERESSE = ["In location", "Rientrato", "Confermato", "Pronto"]
DEFAULT_DATE = "2025-06-06"
EXPECTED_IDS = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]

def parse_arguments():
    """Analizza gli argomenti della linea di comando"""
    parser = argparse.ArgumentParser(description='Recupera progetti Rentman con metodo paginato')
    parser.add_argument('--verbose', action='store_true', help='Mostra informazioni dettagliate')
    parser.add_argument('--data', type=str, default=DEFAULT_DATE, help=f'Data nel formato YYYY-MM-DD (default: {DEFAULT_DATE})')
    return parser.parse_args()

def print_separator(message=""):
    """Stampa un separatore con un messaggio opzionale"""
    width = 80
    if message:
        print("\n" + "=" * width)
        print(f"{message.center(width)}")
        print("=" * width)
    else:
        print("\n" + "-" * width)

def print_project_info(project, verbose=False):
    """Stampa informazioni su un progetto in modo leggibile"""
    project_id = project.get('id', 'N/A')
    project_name = project.get('name', 'Senza nome')
    project_status = project.get('status', 'Senza stato')
    project_value = project.get('project_value', 0)
    
    # Formatta il valore del progetto
    if project_value is None:
        value_display = "N/A"
    else:
        try:
            value_display = f"{float(project_value):.2f} €"
        except:
            value_display = f"{project_value} €"
    
    # Info di base
    print(f"ID: {project_id} | {project_name}")
    print(f"  Status: {project_status} | Valore: {value_display}")
    
    # Informazioni aggiuntive se verbose è True
    if verbose:
        period_from = project.get('equipment_period_from', 'N/A')
        period_to = project.get('equipment_period_to', 'N/A')
        project_type = project.get('project_type_name', 'N/A')
        customer = project.get('cliente', 'N/A')
        manager = project.get('manager_name', 'N/A')
        
        print(f"  Periodo: {period_from} → {period_to}")
        print(f"  Tipo progetto: {project_type}")
        print(f"  Cliente: {customer}")
        print(f"  Responsabile: {manager}")
    
    print("-")

def simulate_web_grid_behavior(target_date, verbose=False):
    """Simula il comportamento della grid web dell'applicazione Flask"""
    print_separator(f"RECUPERO PROGETTI RENTMAN (GRID WEB SIMULATION)")
    print(f"🔍 Data target: {target_date}")
    print(f"🔖 Stati di interesse: {', '.join(STATI_INTERESSE)}")
    
    # Misurazione del tempo di esecuzione
    start_time = time.time()
    
    try:
        # FASE 1: Recupero progetti con paginazione (come nella grid web)
        print("\n🚀 FASE 1: Recupero progetti paginato...")
        progetti = list_projects_by_date_paginated_full_unified(target_date, target_date)
        print(f"📊 Progetti recuperati: {len(progetti)}")
        
        # Mostra stati presenti prima del filtro
        stati_presenti_prima = set(p.get('status', '') for p in progetti)
        print(f"📊 Stati presenti (prima del filtro): {sorted(stati_presenti_prima)}")
        
        # FASE 2: Filtraggio per stati (come nella grid web)
        print("\n🚀 FASE 2: Filtraggio per stati di interesse...")
        progetti_filtrati = filter_projects_by_status(progetti, STATI_INTERESSE)
        print(f"📊 Progetti dopo il filtro: {len(progetti_filtrati)}")
        
        # FASE 3: Verifica corrispondenza con lista hardcoded
        print("\n🚀 FASE 3: Verifica corrispondenza con lista attesa...")
        found_ids = set(p.get('id') for p in progetti_filtrati)
        
        # Verifica quali ID dalla lista hardcoded sono stati trovati
        missing_ids = [pid for pid in EXPECTED_IDS if pid not in found_ids]
        extra_ids = [pid for pid in found_ids if pid not in EXPECTED_IDS]
        
        # Rapporto di corrispondenza
        match_percentage = 100.0
        if EXPECTED_IDS:
            match_percentage = ((len(EXPECTED_IDS) - len(missing_ids)) / len(EXPECTED_IDS)) * 100
        
        print(f"📊 Corrispondenza con lista attesa: {match_percentage:.1f}%")
        
        if missing_ids:
            print(f"⚠️ ID attesi ma non trovati ({len(missing_ids)}): {missing_ids}")
        else:
            print("✅ Tutti gli ID attesi sono stati trovati")
        
        if extra_ids:
            print(f"⚠️ ID trovati ma non attesi ({len(extra_ids)}): {extra_ids}")
        else:
            print("✅ Nessun ID extra trovato")
        
        # FASE 4: Visualizzazione risultati
        print_separator("RISULTATI FINALI")
        print(f"📊 Progetti filtrati totali: {len(progetti_filtrati)}")
        print(f"⏱️ Tempo di esecuzione: {time.time() - start_time:.2f} secondi")
        
        # Statistiche finali
        stati_finali = {}
        for p in progetti_filtrati:
            stato = p.get('status', 'N/A')
            stati_finali[stato] = stati_finali.get(stato, 0) + 1
        
        print("\nDistribuzione per stato:")
        for stato, conteggio in sorted(stati_finali.items()):
            print(f"  - {stato}: {conteggio} progetti")
        
        # Mostra progetti se richiesto
        if verbose or len(progetti_filtrati) <= 30:
            print_separator("ELENCO PROGETTI")
            for i, progetto in enumerate(progetti_filtrati, 1):
                print(f"{i}. ", end="")
                print_project_info(progetto, verbose=verbose)
        else:
            print_separator("RIEPILOGO PROGETTI")
            print(f"Trovati {len(progetti_filtrati)} progetti. Usa --verbose per vedere i dettagli.")
            # Mostra solo i primi 5 progetti come esempio
            for i, progetto in enumerate(progetti_filtrati[:5], 1):
                print(f"{i}. ", end="")
                print_project_info(progetto, verbose=False)
            print("...")
        
        return 0
    
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Pulizia delle cache
        clear_cache()

def main():
    """Funzione principale dello script"""
    args = parse_arguments()
    return simulate_web_grid_behavior(args.data, args.verbose)

if __name__ == "__main__":
    sys.exit(main())
