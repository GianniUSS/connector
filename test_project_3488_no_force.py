#!/usr/bin/env python3
"""
Test per verificare il valore del progetto 3488 senza correzioni forzate
"""

import requests
import json

def test_project_3488():
    print("🔍 Test del progetto 3488 senza correzioni forzate")
    
    try:
        # Test endpoint API
        url = "http://127.0.0.1:5000/lista-progetti?from_date=2025-01-01&to_date=2025-12-31"
        print(f"📡 Chiamata API: {url}")
        
        response = requests.get(url)
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            projects = response.json()
            print(f"📋 Progetti totali ricevuti: {len(projects)}")
            
            # Cerca il progetto 3488
            project_3488 = None
            for project in projects:
                if str(project.get('id')) == '3488':
                    project_3488 = project
                    break
            
            if project_3488:
                print("\n🎯 PROGETTO 3488 TROVATO!")
                print(f"  📝 ID: {project_3488.get('id')}")
                print(f"  📄 Nome: {project_3488.get('name')}")
                print(f"  💰 Valore: {project_3488.get('project_value')}")
                print(f"  📊 Status: {project_3488.get('status')}")
                print(f"  🏷️ Type: {project_3488.get('project_type_name')}")
                
                # Verifica se il valore è corretto
                value = project_3488.get('project_value')
                if value == "0.00":
                    print("\n❌ PROBLEMA CONFERMATO: Il valore è 0.00 invece di 14020.00")
                elif value == "14020.00":
                    print("\n✅ PROBLEMA RISOLTO: Il valore è corretto!")
                else:
                    print(f"\n🤔 VALORE INASPETTATO: {value}")
                
                return project_3488
            else:
                print("\n❌ Progetto 3488 non trovato nella risposta!")
                # Mostra i primi progetti per debug
                print("Primi 5 progetti:")
                for i, p in enumerate(projects[:5]):
                    print(f"  {i+1}. ID: {p.get('id')}, Valore: {p.get('project_value')}")
        else:
            print(f"❌ Errore API: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return None

if __name__ == "__main__":
    test_project_3488()
