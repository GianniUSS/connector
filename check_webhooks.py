#!/usr/bin/env python3
"""
Verifica rapida dei webhook salvati
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_config import get_webhooks_from_db

def check_latest_webhooks():
    """Controlla gli ultimi webhook salvati"""
    webhooks, total = get_webhooks_from_db({}, 5, 0)
    
    print(f"Totale webhook: {total}")
    
    if webhooks:
        print("\n🔍 ULTIMI 5 WEBHOOK:")
        for w in webhooks[:5]:
            print(f"ID: {w['id']}")
            print(f"  Fonte: {w['source']}")
            print(f"  Evento: {w.get('event_type', 'N/A')}")
            print(f"  ItemType: {w.get('item_type', 'N/A')}")
            print(f"  Progetto: {w.get('project_id', 'N/A')}")
            print(f"  Utente: {w.get('user_info', 'N/A')}")
            print("-" * 30)
    else:
        print("Nessun webhook trovato")

if __name__ == "__main__":
    check_latest_webhooks()
