#!/usr/bin/env python3
"""
Script per analizzare i dati utente nei webhook
"""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_config import get_db_connection

def analyze_webhook_user_data():
    """Analizza i dati utente nei webhook"""
    connection = get_db_connection(use_database=True)
    if not connection:
        print("❌ Impossibile connettersi al database")
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Prendi un webhook di esempio
        cursor.execute("SELECT id, payload, user_info FROM webhooks WHERE user_info IS NOT NULL LIMIT 1")
        result = cursor.fetchone()
        
        if not result:
            print("❌ Nessun webhook trovato")
            return
        
        print(f"📋 Analisi Webhook ID: {result['id']}")
        print(f"📋 User Info attuale: {result['user_info']}")
        print()
        
        try:
            payload = json.loads(result['payload'])
            print("📋 Payload completo:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print()
            
            if 'user' in payload:
                print("👤 Dati utente disponibili:")
                user_data = payload['user']
                print(json.dumps(user_data, indent=2, ensure_ascii=False))
                print()
                
                # Analizza che campi sono disponibili
                print("🔍 Campi disponibili nell'oggetto user:")
                for key, value in user_data.items():
                    print(f"  - {key}: {value}")
                
            else:
                print("❌ Nessun campo 'user' nel payload")
                
        except json.JSONDecodeError as e:
            print(f"❌ Errore parsing JSON: {e}")
            print(f"Payload raw: {result['payload'][:500]}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    analyze_webhook_user_data()
