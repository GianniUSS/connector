#!/usr/bin/env python3
"""
Script per verificare che la correzione abbia risolto la discrepanza.
Testa entrambe le modalità e confronta i risultati.
"""

import requests
import json
from datetime import datetime

def test_normal_mode():
    """Testa la modalità normale"""
    print("=== TESTING NORMAL MODE ===")
    
    url = "http://localhost:5000/lista-progetti"
    payload = {
        "fromDate": "2025-06-05",
        "toDate": "2025-06-05"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        projects = data.get('projects', [])
        print(f"Normal mode - Projects count: {len(projects)}")
        
        # Mostra tutti i progetti con i loro stati
        for project in projects:
            project_id = project.get('id')
            project_number = project.get('number')
            status = project.get('status', 'N/A')
            print(f"  Project {project_id} (#{project_number}): {status}")
        
        return projects
        
    except Exception as e:
        print(f"Error in normal mode: {e}")
        return []

def test_paginated_mode():
    """Testa la modalità paginata"""
    print("\n=== TESTING PAGINATED MODE ===")
    
    url = "http://localhost:5000/lista-progetti-paginati"
    payload = {
        "fromDate": "2025-06-05",
        "toDate": "2025-06-05",
        "pageSize": 50
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        projects = data.get('projects', [])
        print(f"Paginated mode - Projects count: {len(projects)}")
        
        # Mostra tutti i progetti con i loro stati
        for project in projects:
            project_id = project.get('id')
            project_number = project.get('number')
            status = project.get('status', 'N/A')
            print(f"  Project {project_id} (#{project_number}): {status}")
        
        return projects
        
    except Exception as e:
        print(f"Error in paginated mode: {e}")
        return []

def compare_results(normal_projects, paginated_projects):
    """Confronta i risultati delle due modalità"""
    print("\n=== COMPARISON RESULTS ===")
    
    print(f"Normal mode count: {len(normal_projects)}")
    print(f"Paginated mode count: {len(paginated_projects)}")
    
    if len(normal_projects) == len(paginated_projects):
        print("✅ PROJECT COUNT MATCHES!")
    else:
        print("❌ PROJECT COUNT MISMATCH!")
        return False
    
    # Crea dizionari per il confronto
    normal_dict = {p['id']: p for p in normal_projects}
    paginated_dict = {p['id']: p for p in paginated_projects}
    
    # Verifica che gli stessi progetti siano presenti
    normal_ids = set(normal_dict.keys())
    paginated_ids = set(paginated_dict.keys())
    
    if normal_ids == paginated_ids:
        print("✅ SAME PROJECT IDs!")
    else:
        print("❌ DIFFERENT PROJECT IDs!")
        missing_in_paginated = normal_ids - paginated_ids
        missing_in_normal = paginated_ids - normal_ids
        
        if missing_in_paginated:
            print(f"Missing in paginated: {missing_in_paginated}")
        if missing_in_normal:
            print(f"Missing in normal: {missing_in_normal}")
        return False
    
    # Verifica che gli stati siano consistenti
    print("\n=== STATUS COMPARISON ===")
    status_mismatches = []
    
    for project_id in normal_ids:
        normal_status = normal_dict[project_id].get('status', 'N/A')
        paginated_status = paginated_dict[project_id].get('status', 'N/A')
        
        if normal_status != paginated_status:
            status_mismatches.append({
                'id': project_id,
                'number': normal_dict[project_id].get('number'),
                'normal_status': normal_status,
                'paginated_status': paginated_status
            })
    
    if not status_mismatches:
        print("✅ ALL STATUS VALUES MATCH!")
        return True
    else:
        print("❌ STATUS MISMATCHES FOUND:")
        for mismatch in status_mismatches:
            print(f"  Project {mismatch['id']} (#{mismatch['number']}):")
            print(f"    Normal: {mismatch['normal_status']}")
            print(f"    Paginated: {mismatch['paginated_status']}")
        return False

def main():
    print("VERIFYING FIX FOR PROJECT DISCREPANCY")
    print("=" * 50)
    
    # Testa entrambe le modalità
    normal_projects = test_normal_mode()
    paginated_projects = test_paginated_mode()
    
    if not normal_projects or not paginated_projects:
        print("❌ Failed to get data from one or both modes")
        return
    
    # Confronta i risultati
    success = compare_results(normal_projects, paginated_projects)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 FIX VERIFICATION: SUCCESS!")
        print("Both modes now return identical results.")
    else:
        print("❌ FIX VERIFICATION: FAILED!")
        print("Discrepancies still exist between the two modes.")
    
    # Focus specifico sul progetto 3120 che era il problema
    print("\n=== PROJECT 3120 SPECIFIC CHECK ===")
    project_3120_normal = next((p for p in normal_projects if p['id'] == 3120), None)
    project_3120_paginated = next((p for p in paginated_projects if p['id'] == 3120), None)
    
    if project_3120_normal and project_3120_paginated:
        print(f"Project 3120 normal status: {project_3120_normal.get('status')}")
        print(f"Project 3120 paginated status: {project_3120_paginated.get('status')}")
        
        if project_3120_normal.get('status') == project_3120_paginated.get('status'):
            print("✅ Project 3120 status is now consistent!")
        else:
            print("❌ Project 3120 status still inconsistent!")
    elif project_3120_normal and not project_3120_paginated:
        print("❌ Project 3120 still missing from paginated mode!")
    elif not project_3120_normal and project_3120_paginated:
        print("❌ Project 3120 missing from normal mode!")
    else:
        print("❌ Project 3120 missing from both modes!")

if __name__ == "__main__":
    main()