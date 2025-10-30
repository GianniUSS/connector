#!/usr/bin/env python3
"""
Verifica finale che la dashboard mostri i nomi utente aggiornati
"""

import requests

def verify_dashboard_users():
    """Verifica che la dashboard mostri i nomi degli utenti"""
    print("🔍 VERIFICA FINALE - Nomi utente nella dashboard")
    print("=" * 60)
    
    try:
        response = requests.get('http://localhost:5000/webhooks?per_page=10')
        
        if response.status_code != 200:
            print(f"❌ Errore API: {response.status_code}")
            return
        
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ API error: {data.get('error')}")
            return
        
        webhooks = data.get('webhooks', [])
        print(f"✅ API OK - {len(webhooks)} webhook recuperati")
        
        if not webhooks:
            print("⚠️  Nessun webhook da verificare")
            return
        
        print(f"\n📊 WEBHOOK CON NOMI UTENTE:")
        print("-" * 80)
        print(f"{'ID':<4} {'Utente':<25} {'ItemType':<15} {'Evento':<12} {'Ricevuto':<10}")
        print("-" * 80)
        
        for webhook in webhooks:
            webhook_id = str(webhook.get('id', 'N/A'))
            user_info = webhook.get('user_info', 'N/A')
            item_type = webhook.get('item_type', 'N/A')
            event_type = webhook.get('event_type', 'N/A')
            received_at = webhook.get('received_at', 'N/A')
            if received_at != 'N/A':
                received_at = received_at.split()[0]  # Solo la data
            
            print(f"{webhook_id:<4} {user_info:<25} {item_type:<15} {event_type:<12} {received_at:<10}")
        
        # Verifica che non ci siano più ID
        id_format_count = sum(1 for w in webhooks if w.get('user_info', '').startswith('ID:'))
        name_format_count = sum(1 for w in webhooks if w.get('user_info') and not w.get('user_info', '').startswith('ID:'))
        
        print(f"\n🎯 RISULTATI:")
        print(f"  📋 Totale webhook: {len(webhooks)}")
        print(f"  ✅ Con nomi utente: {name_format_count}")
        print(f"  ❌ Con formato ID: {id_format_count}")
        
        if id_format_count == 0:
            print(f"\n🎉 PERFETTO! Tutti i webhook mostrano i nomi degli utenti!")
        else:
            print(f"\n⚠️  Ci sono ancora {id_format_count} webhook con formato ID")
        
        print(f"\n🌐 Dashboard: http://localhost:5000/webhook-manager.html")
        
    except Exception as e:
        print(f"❌ Errore durante verifica: {e}")

if __name__ == "__main__":
    verify_dashboard_users()
