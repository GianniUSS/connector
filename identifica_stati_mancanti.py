#!/usr/bin/env python3
"""
🔍 IDENTIFICAZIONE STATI PROGETTI MANCANTI
Analizza gli stati esatti dei progetti per trovare i 3 mancanti (9-6=3)
"""

import sys
import os
import requests
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def identifica_stati_mancanti():
    """Identifica gli stati esatti dei progetti mancanti"""
    
    print("🔍 IDENTIFICAZIONE STATI PROGETTI MANCANTI")
    print("=" * 55)
    print("🎯 Obiettivo: Trovare gli stati dei 3 progetti mancanti")
    print("📊 Rentman UI: 9 progetti | AppConnector: 6 progetti")
    print("=" * 55)
    
    try:
        import config
        from datetime import datetime
        
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        print("🔄 Recuperando progetti per 06/06/2025...")
        
        # Recupera progetti dall'API
        url = f"{config.REN_BASE_URL}/projects"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.ok:
            projects = response.json().get('data', [])
            print(f"  📦 Progetti totali dall'API: {len(projects)}")
            
            # Filtra per data 6 giugno 2025 (SOLO filtro date)
            target_date = datetime.strptime("2025-06-06", "%Y-%m-%d").date()
            progetti_06_06 = []
            
            for p in projects:
                period_start = p.get('planperiod_start')
                period_end = p.get('planperiod_end')
                
                if not period_start or not period_end:
                    continue
                
                try:
                    ps = datetime.fromisoformat(period_start[:10]).date()
                    pe = datetime.fromisoformat(period_end[:10]).date()
                    
                    if ps <= target_date <= pe:
                        progetti_06_06.append(p)
                except Exception:
                    continue
            
            print(f"📅 Progetti che includono 06/06/2025 (solo filtro date): {len(progetti_06_06)}")
            
            # Recupera gli stati reali per ogni progetto
            print(f"\n🔄 Recuperando stati reali dei progetti...")
            progetti_con_stati = []
            
            for i, p in enumerate(progetti_06_06):
                project_id = p.get('id')
                status_path = p.get('status', '')
                
                # Estrai stato reale dall'API
                status_name = "Sconosciuto"
                if status_path and status_path.startswith('/statuses/'):
                    try:
                        status_id = status_path.split('/')[-1]
                        status_url = f"{config.REN_BASE_URL}/statuses/{status_id}"
                        status_response = requests.get(status_url, headers=headers, timeout=5)
                        
                        if status_response.ok:
                            status_data = status_response.json().get('data', {})
                            status_name = status_data.get('name', f'Status_{status_id}')
                        else:
                            status_name = f'Status_{status_id}'
                    except Exception as e:
                        status_name = f'Errore_{str(e)[:10]}'
                
                progetti_con_stati.append({
                    'id': project_id,
                    'name': p.get('name', 'N/A')[:50],
                    'status': status_name,
                    'status_path': status_path,
                    'period_start': p.get('planperiod_start', 'N/A')[:10],
                    'period_end': p.get('planperiod_end', 'N/A')[:10]
                })
                
                # Progress indicator
                if (i + 1) % 3 == 0 or (i + 1) == len(progetti_06_06):
                    print(f"  📊 Processati {i + 1}/{len(progetti_06_06)} progetti...")
            
            print(f"\n📋 TUTTI I PROGETTI 06/06/2025 CON STATI:")
            print(f"{'ID':<6} | {'STATO':<25} | {'PROGETTO':<40} | {'PERIODO'}")
            print("-" * 100)
            
            # Raggruppa per stato
            progetti_per_stato = {}
            for p in progetti_con_stati:
                stato = p['status']
                if stato not in progetti_per_stato:
                    progetti_per_stato[stato] = []
                progetti_per_stato[stato].append(p)
            
            total_count = 0
            for stato, progetti_lista in sorted(progetti_per_stato.items()):
                count = len(progetti_lista)
                total_count += count
                
                print(f"\n🏷️  STATO: {stato} ({count} progetti)")
                print("-" * 80)
                
                for p in progetti_lista:
                    print(f"{p['id']:<6} | {stato:<25} | {p['name']:<40} | {p['period_start']} → {p['period_end']}")
            
            print(f"\n📊 RIEPILOGO STATI:")
            for stato, progetti_lista in sorted(progetti_per_stato.items(), key=lambda x: len(x[1]), reverse=True):
                print(f"  {len(progetti_lista):2d} progetti: {stato}")
            
            print(f"\n🎯 ANALISI FILTRI APPCONNECTOR:")
            
            # Stati validi attuali dell'AppConnector
            stati_validi_appconnector = {
                'confermato', 'confirmed', 
                'in location', 'on location',
                'rientrato', 'returned',
                'in location / annullato', 'on location / cancelled',
                'rientrato / concept', 'returned / concept'
            }
            
            stati_esclusi = {'annullato', 'concept', 'concetto'}
            
            progetti_inclusi = []
            progetti_esclusi = []
            
            for stato, progetti_lista in progetti_per_stato.items():
                stato_lower = stato.lower().strip()
                
                # Verifica se passa i filtri AppConnector
                if stato_lower in stati_validi_appconnector and stato_lower not in stati_esclusi:
                    progetti_inclusi.extend(progetti_lista)
                    print(f"  ✅ {stato}: {len(progetti_lista)} progetti INCLUSI")
                else:
                    progetti_esclusi.extend(progetti_lista)
                    print(f"  ❌ {stato}: {len(progetti_lista)} progetti ESCLUSI dai filtri")
            
            print(f"\n🎯 RISULTATO FINALE:")
            print(f"  📊 Rentman UI: 9 progetti")
            print(f"  📡 API (solo date): {total_count} progetti")
            print(f"  ✅ AppConnector (inclusi): {len(progetti_inclusi)} progetti")
            print(f"  ❌ AppConnector (esclusi): {len(progetti_esclusi)} progetti")
            
            if len(progetti_esclusi) == 3:
                print(f"\n🎉 TROVATI I 3 PROGETTI MANCANTI!")
                print(f"📋 PROGETTI ESCLUSI DAI FILTRI:")
                for p in progetti_esclusi:
                    print(f"    ID {p['id']}: {p['name']}")
                    print(f"        Stato: {p['status']}")
                    print(f"        Periodo: {p['period_start']} → {p['period_end']}")
                    print()
                
                print(f"💡 SOLUZIONE:")
                stati_da_aggiungere = set(p['status'].lower().strip() for p in progetti_esclusi)
                print(f"   Aggiungi questi stati ai filtri validi:")
                for stato in sorted(stati_da_aggiungere):
                    print(f"     '{stato}'")
            
            return len(progetti_esclusi)
            
        else:
            print(f"❌ Errore API: {response.status_code}")
            return -1
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
        return -1

if __name__ == "__main__":
    count = identifica_stati_mancanti()
    print(f"\n{'=' * 55}")
    if count >= 0:
        print(f"🎯 PROGETTI MANCANTI IDENTIFICATI: {count}")
    else:
        print("❌ IDENTIFICAZIONE FALLITA!")
