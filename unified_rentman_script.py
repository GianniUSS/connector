#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script unificato per recupero progetti Rentman
==============================================
Questo script utilizza le stesse funzioni della grid web per recuperare e filtrare 
i progetti per una data specifica (06/06/2025), assicurando coerenza tra
lo script standalone e la visualizzazione web.

Utilizzo:
  python unified_rentman_script.py

Output:
  La lista dei progetti per il 06/06/2025 filtrati per gli stati di interesse:
  - In location
  - Rientrato
  - Confermato
  - Pronto
"""

import sys
import time
from datetime import datetime
from rentman_projects_fixed_clean import (
    list_projects_by_date_unified,
    list_projects_by_date_paginated_full_unified,
    filter_projects_by_status,
    clear_cache
)

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

def main():
    """Funzione principale dello script"""
    print_separator("RECUPERO PROGETTI RENTMAN UNIFICATO")
    
    # Data target
    target_date = "2025-06-06"
    
    # Stati di interesse (gli stessi utilizzati nella grid web)
    stati_interesse = ["In location", "Rientrato", "Confermato", "Pronto"]
    
    print(f"🔍 Recupero progetti per data: {target_date}")
    print(f"🔖 Stati di interesse: {', '.join(stati_interesse)}")
    
    # Misurazione del tempo di esecuzione
    start_time = time.time()
    
    try:
        # Fase 1: Recupero dei progetti per la data target
        print("\n🚀 FASE 1: Recupero progetti...")
        
        # Metodo standard (non paginato)
        print_separator("Metodo standard")
        try:
            progetti_standard = list_projects_by_date_unified(target_date, target_date)
            print(f"✅ Recuperati {len(progetti_standard)} progetti (metodo standard)")
        except Exception as e:
            print(f"❌ Errore nel recupero progetti (metodo standard): {e}")
            progetti_standard = []
        
        # Metodo paginato (più robusto)
        print_separator("Metodo paginato (più robusto)")
        try:
            progetti_paginati = list_projects_by_date_paginated_full_unified(target_date, target_date)
            print(f"✅ Recuperati {len(progetti_paginati)} progetti (metodo paginato)")
        except Exception as e:
            print(f"❌ Errore nel recupero progetti (metodo paginato): {e}")
            progetti_paginati = []
        
        # Scegli il metodo che ha avuto successo
        if progetti_paginati:
            progetti = progetti_paginati
            metodo_usato = "paginato"
        else:
            progetti = progetti_standard
            metodo_usato = "standard"
        
        if not progetti:
            print("❌ Nessun progetto recuperato. Impossibile continuare.")
            return 1
        
        # Fase 2: Filtraggio per stati di interesse
        print("\n🚀 FASE 2: Filtraggio per stati...")
        print(f"📊 Progetti prima del filtro: {len(progetti)}")
        
        # Recupera tutti gli stati presenti
        stati_presenti = set(p.get('status', '') for p in progetti)
        print(f"📊 Stati presenti nei progetti: {sorted(stati_presenti)}")
        
        # Filtra i progetti per gli stati di interesse
        progetti_filtrati = filter_projects_by_status(progetti, stati_interesse)
        print(f"📊 Progetti dopo il filtro: {len(progetti_filtrati)}")
        
        # Fase 3: Controllo hardcoded
        print("\n🚀 FASE 3: Verifica con lista hardcoded...")
        expected_ids = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]
        found_ids = set(p.get('id') for p in progetti_filtrati)
        
        # Verifica quali ID dalla lista hardcoded sono stati trovati
        missing_ids = [pid for pid in expected_ids if pid not in found_ids]
        extra_ids = [pid for pid in found_ids if pid not in expected_ids]
        
        if missing_ids:
            print(f"⚠️ ID attesi ma non trovati: {missing_ids}")
        else:
            print("✅ Tutti gli ID attesi sono stati trovati")
        
        if extra_ids:
            print(f"⚠️ ID trovati ma non attesi: {extra_ids}")
        else:
            print("✅ Nessun ID extra trovato")
        
        if not missing_ids and not extra_ids:
            print("✅ Perfetta corrispondenza con la lista hardcoded!")
        
        # Fase 4: Visualizzazione risultati
        print_separator("RISULTATI FINALI")
        print(f"📊 Progetti filtrati: {len(progetti_filtrati)} (metodo {metodo_usato})")
        print(f"⏱️ Tempo di esecuzione: {time.time() - start_time:.2f} secondi")
        
        # Mostra i progetti
        print_separator("ELENCO PROGETTI")
        for i, progetto in enumerate(progetti_filtrati, 1):
            print(f"{i}. ", end="")
            print_project_info(progetto, verbose=False)
        
        # Riepilogo statistiche
        stati_filtrati = {}
        for p in progetti_filtrati:
            stato = p.get('status', 'N/A')
            stati_filtrati[stato] = stati_filtrati.get(stato, 0) + 1
        
        print_separator("STATISTICHE")
        print("Distribuzione per stato:")
        for stato, conteggio in sorted(stati_filtrati.items()):
            print(f"  - {stato}: {conteggio} progetti")
        
        return 0
    
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        return 1
    finally:
        # Pulizia delle cache
        clear_cache()

if __name__ == "__main__":
    sys.exit(main())
