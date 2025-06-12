#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script che simula il comportamento del pulsante "recupera progetti" della web app
===============================================================================
Questo script replica esattamente la stessa logica utilizzata dal pulsante
"recupera progetti" dell'interfaccia web, assicurando una perfetta coerenza
tra lo script standalone e l'applicazione Flask.

Simula la chiamata all'endpoint della web app e utilizza le stesse funzioni
per recuperare e filtrare i progetti Rentman.

Utilizzo:
  python simulate_webapp_button.py [--data YYYY-MM-DD]

Opzioni:
  --data       Specifica la data nel formato YYYY-MM-DD (default: 2025-06-06)
"""

import sys
import time
import json
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
    parser = argparse.ArgumentParser(description='Simula il pulsante "recupera progetti" della web app')
    parser.add_argument('--data', type=str, default=DEFAULT_DATE, help=f'Data nel formato YYYY-MM-DD (default: {DEFAULT_DATE})')
    parser.add_argument('--output', type=str, choices=['console', 'json'], default='console', help='Formato output (default: console)')
    parser.add_argument('--file', type=str, help='File di output (solo per formato json)')
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

def simulate_webapp_button(target_date, output_format='console', output_file=None):
    """Simula il pulsante 'recupera progetti' della web app"""
    if output_format == 'console':
        print_separator("SIMULAZIONE PULSANTE 'RECUPERA PROGETTI'")
        print(f"🔍 Data target: {target_date}")
        print(f"🔖 Stati di interesse: {', '.join(STATI_INTERESSE)}")
    
    # Misurazione del tempo di esecuzione
    start_time = time.time()
    
    try:
        # Converti la data nel formato corretto
        try:
            # Verifica che la data sia nel formato corretto
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d")
            from_date = to_date = target_date
        except ValueError:
            if output_format == 'console':
                print(f"❌ Formato data non valido: {target_date}. Uso data predefinita: {DEFAULT_DATE}")
            from_date = to_date = DEFAULT_DATE
        
        # SIMULAZIONE ENDPOINT FLASK
        # Questo codice simula esattamente ciò che succede nell'endpoint Flask
        # quando si preme il pulsante "recupera progetti"
        
        if output_format == 'console':
            print("\n🚀 Simulazione richiesta all'endpoint...")
        
        # --- INIZIO CODICE DELL'ENDPOINT ---
        page_size = 50  # Forza page_size massimo per robustezza
        
        # Recupero progetti (stesso codice di app.py)
        progetti = list_projects_by_date_paginated_full_unified(from_date, to_date, page_size)
        
        # Filtro grid: solo stati di interesse (stesso codice di app.py)
        progetti_filtrati = filter_projects_by_status(progetti, STATI_INTERESSE)
        
        # Formattazione output per la grid (stesso codice di app.py)
        output_data = []
        for p in progetti_filtrati:
            project_value = p.get('project_value')
            if project_value is None:
                display_value = 'N/A'
            else:
                try:
                    display_value = f"{float(project_value):.2f} €"
                except:
                    display_value = f"{project_value} €"
            
            # Costruzione riga per la grid
            grid_row = {
                "id": p.get("id"),
                "number": p.get("number", ""),
                "name": p.get("name", ""),
                "status": p.get("status", ""),
                "value": display_value,
                "date_from": p.get("equipment_period_from", ""),
                "date_to": p.get("equipment_period_to", ""),
                "type": p.get("project_type_name", ""),
                "customer": p.get("cliente", ""),
                "manager": p.get("manager_name", "")
            }
            output_data.append(grid_row)
        # --- FINE CODICE DELL'ENDPOINT ---
        
        # Output dei risultati
        if output_format == 'console':
            # Statistiche finali
            print_separator("RISULTATI DELLA SIMULAZIONE")
            print(f"📊 Progetti totali recuperati: {len(progetti)}")
            print(f"📊 Progetti dopo filtro stati: {len(progetti_filtrati)}")
            print(f"⏱️ Tempo di esecuzione: {time.time() - start_time:.2f} secondi")
            
            # Distribuzione stati
            stati_finali = {}
            for p in progetti_filtrati:
                stato = p.get('status', 'N/A')
                stati_finali[stato] = stati_finali.get(stato, 0) + 1
            
            print("\nDistribuzione per stato:")
            for stato, conteggio in sorted(stati_finali.items()):
                print(f"  - {stato}: {conteggio} progetti")
            
            # Verifica corrispondenza con lista hardcoded
            found_ids = set(p.get('id') for p in progetti_filtrati)
            missing_ids = [pid for pid in EXPECTED_IDS if pid not in found_ids]
            extra_ids = [pid for pid in found_ids if pid not in EXPECTED_IDS]
            
            print("\nVerifica corrispondenza con lista attesa:")
            if missing_ids:
                print(f"⚠️ ID attesi ma non trovati ({len(missing_ids)}): {missing_ids}")
            else:
                print("✅ Tutti gli ID attesi sono stati trovati")
            
            if extra_ids:
                print(f"⚠️ ID trovati ma non attesi ({len(extra_ids)}): {extra_ids}")
            else:
                print("✅ Nessun ID extra trovato")
            
            # Mostra progetti
            print_separator("PREVIEW GRID DATI")
            print(f"{'ID':<8} {'STATO':<15} {'NOME':<30} {'VALORE':<15}")
            print("-" * 80)
            for p in output_data[:10]:  # Mostra solo i primi 10
                print(f"{p['id']:<8} {p['status'][:15]:<15} {p['name'][:30]:<30} {p['value']:<15}")
            
            if len(output_data) > 10:
                print("... altri progetti omessi ...")
        
        elif output_format == 'json':
            # Output JSON (come quello che riceve il frontend)
            result = {
                "success": True,
                "data": output_data,
                "count": len(output_data),
                "execution_time": f"{time.time() - start_time:.2f} sec"
            }
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                if output_format == 'console':
                    print(f"✅ Dati salvati in: {output_file}")
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return 0
    
    except Exception as e:
        if output_format == 'console':
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
    return simulate_webapp_button(args.data, args.output, args.file)

if __name__ == "__main__":
    sys.exit(main())
