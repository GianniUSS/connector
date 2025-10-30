#!/usr/bin/env python3
"""
Script per aggiornare i webhook esistenti recuperando i nomi utente da Rentman
usando gli ID già salvati
"""

import json
import logging
import requests
import sys
import os

# Aggiungi il path per importare i moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db_config import get_db_connection, get_rentman_user_name
import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def update_rentman_webhook_users():
    """Aggiorna i webhook di Rentman sostituendo ID:xxxx con i nomi degli utenti"""
    connection = get_db_connection(use_database=True)
    if not connection:
        logging.error("Impossibile connettersi al database")
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Recupera webhook di Rentman con user_info che inizia con "ID:"
        query = """
        SELECT id, user_info, payload 
        FROM webhooks 
        WHERE source = 'rentman' 
        AND user_info LIKE 'ID:%'
        ORDER BY received_at DESC
        """
        
        cursor.execute(query)
        webhooks = cursor.fetchall()
        
        logging.info(f"Trovati {len(webhooks)} webhook Rentman da aggiornare")
        
        updated_count = 0
        error_count = 0
        
        for webhook in webhooks:
            webhook_id = webhook['id']
            old_user_info = webhook['user_info']
            
            # Estrai l'ID utente dal formato "ID:1813"
            try:
                user_id = old_user_info.split(':')[1] if ':' in old_user_info else None
                
                if user_id and user_id.isdigit():
                    # Recupera il nome da Rentman
                    user_name = get_rentman_user_name(int(user_id))
                    
                    if user_name:
                        # Aggiorna il webhook
                        update_query = """
                        UPDATE webhooks 
                        SET user_info = %s 
                        WHERE id = %s
                        """
                        
                        cursor.execute(update_query, (user_name, webhook_id))
                        
                        logging.info(f"✅ Webhook {webhook_id}: '{old_user_info}' -> '{user_name}'")
                        updated_count += 1
                    else:
                        logging.warning(f"⚠️  Webhook {webhook_id}: Nome non trovato per {old_user_info}")
                        error_count += 1
                else:
                    logging.warning(f"⚠️  Webhook {webhook_id}: ID non valido in '{old_user_info}'")
                    error_count += 1
                    
            except Exception as e:
                logging.error(f"❌ Errore processando webhook {webhook_id}: {e}")
                error_count += 1
        
        connection.commit()
        
        logging.info(f"AGGIORNAMENTO COMPLETATO:")
        logging.info(f"  ✅ Aggiornati: {updated_count}")
        logging.info(f"  ❌ Errori: {error_count}")
        
        return True
        
    except Exception as e:
        logging.error(f"Errore aggiornamento webhook: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def test_single_user():
    """Test per un singolo utente"""
    user_id = 1813  # ID che vediamo spesso nei webhook
    
    print(f"🧪 Test recupero nome per utente ID {user_id}")
    
    name = get_rentman_user_name(user_id)
    
    if name:
        print(f"✅ Trovato: ID {user_id} -> {name}")
    else:
        print(f"❌ Nome non trovato per ID {user_id}")

def verify_current_webhooks():
    """Verifica i webhook attuali"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Conta webhook per tipo di user_info
        queries = {
            "Totale": "SELECT COUNT(*) as count FROM webhooks WHERE user_info IS NOT NULL",
            "Con ID": "SELECT COUNT(*) as count FROM webhooks WHERE user_info LIKE 'ID:%'",
            "Con nomi": "SELECT COUNT(*) as count FROM webhooks WHERE user_info IS NOT NULL AND user_info NOT LIKE 'ID:%'",
            "Rentman totale": "SELECT COUNT(*) as count FROM webhooks WHERE source = 'rentman' AND user_info IS NOT NULL",
            "Rentman con ID": "SELECT COUNT(*) as count FROM webhooks WHERE source = 'rentman' AND user_info LIKE 'ID:%'"
        }
        
        stats = {}
        for name, query in queries.items():
            cursor.execute(query)
            stats[name] = cursor.fetchone()['count']
        
        print(f"\n📊 STATISTICHE ATTUALI:")
        for name, count in stats.items():
            print(f"  {name}: {count}")
        
        # Mostra esempi
        cursor.execute("SELECT user_info, COUNT(*) as count FROM webhooks WHERE user_info IS NOT NULL GROUP BY user_info ORDER BY count DESC LIMIT 5")
        examples = cursor.fetchall()
        
        print(f"\n🔍 ESEMPI USER_INFO PIÙ COMUNI:")
        for ex in examples:
            print(f"  '{ex['user_info']}': {ex['count']} volte")
        
    except Exception as e:
        logging.error(f"Errore verifica: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🔄 Aggiornamento nomi utente webhook Rentman")
    print("=" * 60)
    
    print("📋 Stato attuale:")
    verify_current_webhooks()
    
    print(f"\n🧪 Test singolo utente:")
    test_single_user()
    
    print(f"\n🚀 Avvio aggiornamento completo...")
    success = update_rentman_webhook_users()
    
    if success:
        print(f"\n📋 Stato dopo aggiornamento:")
        verify_current_webhooks()
        print(f"\n✅ Aggiornamento completato!")
        print(f"🌐 Ricarica la dashboard: http://localhost:5000/webhook-manager.html")
    else:
        print(f"\n❌ Aggiornamento fallito")

if __name__ == "__main__":
    main()
