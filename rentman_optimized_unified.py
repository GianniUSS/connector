#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script ottimizzato e unificato per Rentman
==========================================
Questo script utilizza la paginazione e i filtri espliciti dell'API Rentman per
recuperare esattamente i progetti per la data 06/06/2025 con un'unica chiamata API.
Unisce i punti di forza dello script originale con le funzioni della web app.
"""

import requests
import config
import json
import time
import sys
from datetime import datetime
import rentman_project_utils

# Configurazione
STATI_INTERESSE = ["In location", "Rientrato", "Confermato", "Pronto"]
DEFAULT_DATE = "2025-06-06"
EXPECTED_IDS = [3120, 3134, 3137, 3152, 3205, 3214, 3298, 3430, 3434, 3438, 3488, 3489, 3490, 3493, 3501, 3536, 3543, 3582, 3602, 3613, 3630, 3632, 3681, 3708, 3713, 3742, 3757, 3779]

def print_separator(message=""):
    """Stampa un separatore con un messaggio opzionale"""
    width = 80
    if message:
        print("\n" + "=" * width)
        print(f"{message.center(width)}")
        print("=" * width)
    else:
        print("\n" + "-" * width)

def get_projects_optimized(headers, target_date=DEFAULT_DATE, verbose=True):
    """
    Versione ottimizzata che utilizza i filtri dell'API per recuperare
    i progetti esattamente per la data target con meno chiamate API.
    """
    print_separator("RECUPERO PROGETTI OTTIMIZZATO")
    print(f"🔍 Data target: {target_date}")
    
    # Preparazione URL e parametri
    url = f"{config.REN_BASE_URL}/projects"
    
    # PARAMETRI CHIAVE:
    # - id[gt]: 2900 (solo progetti con ID > 2900)
    # - fields: solo i campi necessari
    # - limit: dimensione pagina ottimizzata
    params = {
        'sort': '+id',                     # Ordine crescente per ID
        'id[gt]': 2900,                    # Solo ID > 2900
        'fields': 'id,name,number,planperiod_start,planperiod_end',
        'limit': 150,                      # Dimensione pagina ottimizzata
        'offset': 0
    }
    
    if verbose:
        print(f"URL: {url}")
        print(f"Parametri: {json.dumps(params, indent=2)}")
    
    # Misurazione tempo
    start_time = time.time()
    
    # Recupero progetti (con paginazione)
    all_projects = []
    total_pages = 0
    
    while True:
        total_pages += 1
        if verbose:
            print(f"\n📄 Richiesta pagina {total_pages}: offset={params['offset']}, limit={params['limit']}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            if not response.ok:
                print(f"❌ Errore API: {response.status_code}")
                print(f"Dettagli: {response.text}")
                break
            
            data = response.json()
            page_projects = data.get('data', [])
            
            if verbose:
                print(f"✅ Ricevuti {len(page_projects)} progetti nella pagina {total_pages}")
            
            all_projects.extend(page_projects)
            
            # Se la pagina non è piena, probabilmente è l'ultima
            if len(page_projects) < params['limit']:
                break
            
            # Prepara la pagina successiva
            params['offset'] += params['limit']
            
        except Exception as e:
            print(f"❌ Errore: {e}")
            break
    
    elapsed_time = time.time() - start_time
    print(f"\n✅ Recuperati {len(all_projects)} progetti in {elapsed_time:.2f} secondi")
    print(f"📄 Pagine totali: {total_pages}")
    
    # Analisi degli ID
    found_ids = set(p.get('id') for p in all_projects)
    
    # Verifica quali ID dalla lista hardcoded sono stati trovati
    missing_ids = [pid for pid in EXPECTED_IDS if pid not in found_ids]
    extra_ids = [pid for pid in found_ids if pid not in EXPECTED_IDS]
    
    if missing_ids:
        print(f"\n⚠️ ID attesi ma non trovati: {missing_ids}")
        print(f"  Mancanti: {len(missing_ids)}/{len(EXPECTED_IDS)}")
    else:
        print(f"\n✅ Tutti i {len(EXPECTED_IDS)} ID attesi sono stati trovati!")
    
    if extra_ids:
        print(f"\n⚠️ ID trovati ma non attesi: {len(extra_ids)} extra")
        if verbose and len(extra_ids) < 20:
            print(f"  Extra: {sorted(extra_ids)}")
    else:
        print(f"\n✅ Nessun ID extra trovato oltre ai {len(EXPECTED_IDS)} attesi")
    
    # Filtro locale per la data target (usa funzione modulo)
    filtered_projects = rentman_project_utils.filter_projects_by_date(all_projects, target_date)
    print(f"\n✅ Progetti dopo filtro data {target_date}: {len(filtered_projects)}/{len(all_projects)}")
    return filtered_projects

def process_and_filter_projects(projects, headers, target_date=DEFAULT_DATE):
    """
    Processa i progetti e filtra per stati di interesse
    Utilizza la stessa logica di filtro della grid web
    """
    print_separator("FILTRO PER STATI")
    print(f"🔖 Stati di interesse: {', '.join(STATI_INTERESSE)}")
    
    start_time = time.time()
    
    base_url = config.REN_BASE_URL
    # Correggi: passa base_url a get_status_map
    status_map = rentman_project_utils.get_status_map(headers, base_url)
    print(f"📊 Status map caricata: {len(status_map)} stati")
    
    # Converti stati di interesse in lowercase per confronto case-insensitive
    stati_set = set(s.lower() for s in STATI_INTERESSE)
    
    # Processa ogni progetto
    processed_projects = []
    
    # Usa la funzione del modulo per filtro stato
    filtered = rentman_project_utils.filter_projects_by_status(projects, headers, STATI_INTERESSE, base_url)
    for p, status_name in filtered:
        project_id = p.get('id')
        # Recupera dettagli progetto
        project_url = f"{base_url}/projects/{project_id}"
        resp = requests.get(project_url, headers=headers, timeout=10)
        if not resp.ok:
            continue
        data = resp.json().get('data', {})
        # Cliente
        customer_name = ""
        customer_path = data.get('customer')
        if customer_path:
            customer_id = rentman_project_utils.extract_id_from_path(customer_path)
            if customer_id:
                customer_url = f"{base_url}/contacts/{customer_id}"
                cust_resp = requests.get(customer_url, headers=headers, timeout=10)
                if cust_resp.ok:
                    cust_data = cust_resp.json().get('data', {})
                    customer_name = cust_data.get('displayname') or cust_data.get('name', '')
        # Responsabile
        manager_name = None
        manager_email = None
        account_manager_path = data.get('account_manager')
        if account_manager_path:
            manager_id = rentman_project_utils.extract_id_from_path(account_manager_path)
            if manager_id:
                crew_url = f"{base_url}/crew/{manager_id}"
                crew_resp = requests.get(crew_url, headers=headers, timeout=10)
                if crew_resp.ok:
                    crew_data = crew_resp.json().get('data', {})
                    manager_name = crew_data.get('name') or crew_data.get('displayname')
                    manager_email = crew_data.get('email') or crew_data.get('email_1')
        # Tipo progetto
        project_type_name = ""
        project_type_path = data.get('project_type')
        if project_type_path:
            project_type_id = rentman_project_utils.extract_id_from_path(project_type_path)
            if project_type_id:
                type_url = f"{base_url}/projecttypes/{project_type_id}"
                type_resp = requests.get(type_url, headers=headers, timeout=10)
                if type_resp.ok:
                    type_data = type_resp.json().get('data', {})
                    project_type_name = type_data.get('name', '')
        # Valore progetto
        valore = data.get('project_total_price')
        try:
            valore = round(float(valore), 2) if valore is not None else None
        except Exception:
            valore = None
        processed_projects.append({
            'id': project_id,
            'name': p.get('name', ''),
            'number': p.get('number', ''),
            'status': status_name,
            'value': valore,
            'period_from': p.get('planperiod_start', '')[:10] if p.get('planperiod_start') else '',
            'period_to': p.get('planperiod_end', '')[:10] if p.get('planperiod_end') else '',
            'cliente': customer_name,
            'manager_name': manager_name,
            'manager_email': manager_email,
            'project_type_name': project_type_name
        })
    
    elapsed_time = time.time() - start_time
    print(f"✅ Progetti filtrati: {len(processed_projects)}/{len(projects)} in {elapsed_time:.2f} secondi")
    
    # Analisi risultati
    found_ids = set(p.get('id') for p in processed_projects)
    
    # Verifica quali ID dalla lista hardcoded sono stati trovati
    missing_ids = [pid for pid in EXPECTED_IDS if pid not in found_ids]
    extra_ids = [pid for pid in found_ids if pid not in EXPECTED_IDS]
    
    print_separator("ANALISI RISULTATI")
    
    if missing_ids:
        print(f"⚠️ ID attesi ma non trovati dopo filtro: {missing_ids}")
        print(f"  Mancanti: {len(missing_ids)}/{len(EXPECTED_IDS)}")
    else:
        print(f"✅ Tutti i {len(EXPECTED_IDS)} ID attesi sono stati trovati dopo filtro!")
    
    if extra_ids:
        print(f"⚠️ ID trovati ma non attesi dopo filtro: {len(extra_ids)} extra")
        if len(extra_ids) < 20:
            print(f"  Extra: {sorted(extra_ids)}")
    else:
        print(f"✅ Nessun ID extra trovato dopo filtro")
    
    # Distribuzione stati
    stati_finali = {}
    for p in processed_projects:
        stato = p.get('status', 'N/A')
        stati_finali[stato] = stati_finali.get(stato, 0) + 1
    
    print("\nDistribuzione per stato:")
    for stato, conteggio in sorted(stati_finali.items()):
        print(f"  - {stato}: {conteggio} progetti")
    
    return processed_projects

def main():
    """Funzione principale dello script"""
    print_separator("SCRIPT OTTIMIZZATO E UNIFICATO PER RENTMAN")
    
    # Preparazione headers
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    try:
        # Recupero progetti
        projects = get_projects_optimized(headers, DEFAULT_DATE)
        
        # Filtro progetti
        filtered_projects = process_and_filter_projects(projects, headers, DEFAULT_DATE)
        
        # Stampa risultati
        print_separator("RISULTATI FINALI")
        print(f"📊 Progetti trovati: {len(filtered_projects)}")
        
        # Mostra solo i primi 10 progetti
        if filtered_projects:
            print("\nPrimi 10 progetti (ordinati per ID):")
            for i, p in enumerate(sorted(filtered_projects, key=lambda x: x.get('id', 0))[:10], 1):
                print(f"{i}. ID: {p.get('id')}, Status: {p.get('status')}")
                print(f"   Nome: {p.get('name')}")
                print(f"   Cliente: {p.get('cliente')}")
                print(f"   Valore: {p.get('value')} | Periodo: {p.get('period_from')} → {p.get('period_to')}")
                print(f"   Responsabile: {p.get('manager_name')} | Email: {p.get('manager_email')}")
                print(f"   Tipo progetto: {p.get('project_type_name')}")
                print("-")
        
        if len(filtered_projects) > 10:
            print("... altri progetti omessi ...")
        
        return 0
    
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
