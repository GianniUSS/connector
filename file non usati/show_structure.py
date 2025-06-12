#!/usr/bin/env python3
"""
🗂️ VISUALIZZATORE STRUTTURA PROGETTO ORGANIZZATO
Mostra la struttura del progetto dopo la riorganizzazione
"""

import os
from pathlib import Path

def show_project_structure():
    print("🎉 STRUTTURA PROGETTO ORGANIZZATO")
    print("=" * 50)
    
    base_path = Path("e:/AppConnettor")
    
    # File principali
    print("\n📁 CARTELLA PRINCIPALE (File Produzione):")
    print("-" * 40)
    
    py_files = list(base_path.glob("*.py"))
    core_files = [f for f in py_files if not any(x in f.name.lower() 
                 for x in ['test', 'debug', 'analyz', 'temp'])]
    
    essential_files = ['app.py', 'config.py', 'start_flask.py', 
                      'rentman_projects.py', 'quickbooks_api.py']
    
    for file in essential_files:
        if (base_path / file).exists():
            print(f"  🚀 {file}")
    
    print(f"  📊 Totale file Python core: {len(core_files)}")
    
    # Cartella tests_and_debug
    tests_path = base_path / "tests_and_debug"
    if tests_path.exists():
        print(f"\n📁 CARTELLA TESTS_AND_DEBUG:")
        print("-" * 40)
        
        subdirs = [d for d in tests_path.iterdir() if d.is_dir()]
        for subdir in sorted(subdirs):
            file_count = len(list(subdir.glob("*")))
            icon = "🧪" if "test" in subdir.name else "🐛" if "debug" in subdir.name else "📊" if "analysis" in subdir.name else "📋"
            print(f"  {icon} {subdir.name}/ → {file_count} file")
        
        root_files = [f for f in tests_path.glob("*.py")]
        if root_files:
            print(f"  🚀 File root → {len(root_files)} file")
        
        total_organized = sum(len(list(d.glob("*"))) for d in subdirs) + len(root_files)
        print(f"\n  📊 TOTALE ORGANIZZATO: {total_organized} file")
    
    # Documentazione
    print(f"\n📖 DOCUMENTAZIONE CREATA:")
    print("-" * 40)
    docs = ['README.md', 'RIORGANIZZAZIONE_COMPLETATA.md', 
            '🎉_RIORGANIZZAZIONE_COMPLETATA_🎉.md']
    
    for doc in docs:
        if (base_path / doc).exists():
            print(f"  📄 {doc}")
    
    if (tests_path / "README.md").exists():
        print(f"  📄 tests_and_debug/README.md")
    
    print(f"\n🎯 STATO: RIORGANIZZAZIONE COMPLETATA!")
    print("✅ Pronto per produzione e sviluppo")

if __name__ == "__main__":
    show_project_structure()
