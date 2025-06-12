#!/usr/bin/env python3
"""
🔍 VERIFICA CAMPO FINANCIAL: Controlla se usare 'financial' o 'in_financial'
"""

import requests
import config

def verifica_campo_financial():
    """Verifica quale campo usare per financial nei sottoprogetti"""
    
    print("🔍 VERIFICA CAMPO FINANCIAL NEI SOTTOPROGETTI")
    print("=" * 60)
    
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    
    # Test sui progetti target
    target_ids = [3120, 3205, 3438]
    
    for project_id in target_ids:
        print(f"\n📋 PROGETTO {project_id}:")
        print("-" * 40)
        
        try:
            # 1. Stato del progetto principale
            url = f"{config.REN_BASE_URL}/projects/{project_id}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.ok:
                project_data = response.json().get('data', {})
                main_status = project_data.get('status', 'N/A')
                print(f"   📄 Stato progetto principale: '{main_status}'")
                
                # 2. Sottoprogetti del progetto
                subprojects_url = f"{config.REN_BASE_URL}/projects/{project_id}/subprojects"
                sub_response = requests.get(subprojects_url, headers=headers, timeout=10)
                
                if sub_response.ok:
                    subprojects = sub_response.json().get('data', [])
                    print(f"   📋 Sottoprogetti trovati: {len(subprojects)}")
                    
                    if subprojects:
                        print(f"\n   🔍 ANALISI CAMPI FINANCIAL:")
                        
                        for i, sub in enumerate(subprojects, 1):
                            sub_id = sub.get('id', 'N/A')
                            sub_status = sub.get('status', 'N/A')
                            
                            # Controlla tutti i possibili campi financial
                            financial = sub.get('financial', None)
                            in_financial = sub.get('in_financial', None)
                            
                            print(f"\n     Sub {i} (ID:{sub_id}):")
                            print(f"       Status: '{sub_status}'")
                            print(f"       'financial': {financial} (tipo: {type(financial)})")
                            print(f"       'in_financial': {in_financial} (tipo: {type(in_financial)})")
                            
                            # Evidenzia qual è il campo corretto
                            if in_financial is True:
                                print(f"       ✅ QUESTO USA 'in_financial=True' - CAMPO CORRETTO!")
                            elif financial is True:
                                print(f"       ✅ QUESTO USA 'financial=True' - CAMPO ALTERNATIVO!")
                            else:
                                print(f"       ❌ Nessun campo financial attivo")
                        
                        # Riepilogo per questo progetto
                        financial_count = sum(1 for sub in subprojects if sub.get('financial') is True)
                        in_financial_count = sum(1 for sub in subprojects if sub.get('in_financial') is True)
                        
                        print(f"\n   📊 RIEPILOGO PROGETTO {project_id}:")
                        print(f"       Sottoprogetti con 'financial=True': {financial_count}")
                        print(f"       Sottoprogetti con 'in_financial=True': {in_financial_count}")
                        
                        if in_financial_count > 0:
                            print(f"       ✅ USARE CAMPO: 'in_financial'")
                            
                            # Trova il primo con in_financial=True
                            first_financial = next((sub for sub in subprojects if sub.get('in_financial') is True), None)
                            if first_financial:
                                financial_status = first_financial.get('status', 'N/A')
                                print(f"       🎯 Stato da usare: '{financial_status}' (dal primo in_financial=True)")
                                
                                if financial_status != main_status:
                                    print(f"       ⚠️  STATO DIFFERENTE! Principale: '{main_status}' vs Financial: '{financial_status}'")
                                else:
                                    print(f"       ✅ Stati uguali")
                        elif financial_count > 0:
                            print(f"       ✅ USARE CAMPO: 'financial'")
                            
                            # Trova il primo con financial=True
                            first_financial = next((sub for sub in subprojects if sub.get('financial') is True), None)
                            if first_financial:
                                financial_status = first_financial.get('status', 'N/A')
                                print(f"       🎯 Stato da usare: '{financial_status}' (dal primo financial=True)")
                        else:
                            print(f"       ❌ NESSUN SOTTOPROGETTO FINANCIAL TROVATO!")
                            print(f"       ⚠️  Usare stato del progetto principale: '{main_status}'")
                        
                    else:
                        print(f"   ℹ️  Nessun sottoprogetto (usa stato principale)")
                else:
                    print(f"   ❌ Errore sottoprogetti: {sub_response.status_code}")
            else:
                print(f"   ❌ Errore progetto: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Errore: {e}")
    
    print(f"\n🎯 CONCLUSIONI:")
    print(f"   1. Verificare quale campo è presente nei sottoprogetti")
    print(f"   2. Implementare la logica corretta nel codice di stato")
    print(f"   3. Aggiornare tutte le funzioni che recuperano lo stato")

if __name__ == "__main__":
    verifica_campo_financial()
