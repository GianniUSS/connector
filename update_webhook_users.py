#!/usr/bin/env python3
"""
Script per aggiornare i webhook esistenti nel database
Estrae solo il nome dell'utente invece di ID/email/ref
"""

import json
import logging
from db_config import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def extract_user_name_only(payload_str):
    """Estrae solo il nome dell'utente dal payload"""
    try:
        payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        
        if 'user' in payload:
            user_data = payload['user']
            if isinstance(user_data, dict):
                # Priorità al nome dell'utente
                user_name = (user_data.get('name') or 
                           user_data.get('displayname') or 
                           user_data.get('username') or
                           user_data.get('display_name') or
                           user_data.get('full_name'))
                
                if user_name:
                    return user_name
                else:
                    # Se non c'è il nome, usa l'ID come fallback
                    user_id = user_data.get('id')
                    if user_id:
                        return f"ID:{user_id}"
                    else:
                        return str(user_data)
            else:
                return str(user_data)
        elif 'userId' in payload:
            return f"ID:{payload['userId']}"
        elif 'username' in payload:
            return payload['username']
        elif 'user_id' in payload:
            return f"ID:{payload['user_id']}"
        
        return None
        
    except Exception as e:
        logging.error(f"Errore estrazione nome utente: {e}")
        return None

def update_existing_webhooks():
    """Aggiorna i webhook esistenti per mostrare solo il nome utente"""
    connection = get_db_connection(use_database=True)
    if not connection:
        logging.error("Impossibile connettersi al database")
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Recupera tutti i webhook con user_info che contiene ID o pipe
        query = """
        SELECT id, payload, user_info 
        FROM webhooks 
        WHERE user_info IS NOT NULL 
        AND (user_info LIKE '%ID:%' OR user_info LIKE '%|%')
        """
        
        cursor.execute(query)
        webhooks = cursor.fetchall()
        
        logging.info(f"Trovati {len(webhooks)} webhook da aggiornare")
        
        updated_count = 0
        
        for webhook in webhooks:
            webhook_id = webhook['id']
            old_user_info = webhook['user_info']
            payload = webhook['payload']
            
            # Estrai il nuovo user_info (solo nome)
            new_user_info = extract_user_name_only(payload)
            
            if new_user_info and new_user_info != old_user_info:
                # Aggiorna il webhook
                update_query = """
                UPDATE webhooks 
                SET user_info = %s 
                WHERE id = %s
                """
                
                cursor.execute(update_query, (new_user_info, webhook_id))
                
                logging.info(f"Webhook {webhook_id}: '{old_user_info}' -> '{new_user_info}'")
                updated_count += 1
        
        connection.commit()
        logging.info(f"✅ Aggiornati {updated_count} webhook con il nuovo formato utente")
        
        return True
        
    except Exception as e:
        logging.error(f"Errore aggiornamento webhook: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def verify_updates():
    """Verifica gli aggiornamenti"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Conta webhook con diversi formati user_info
        cursor.execute("SELECT COUNT(*) as total FROM webhooks WHERE user_info IS NOT NULL")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as with_id FROM webhooks WHERE user_info LIKE '%ID:%'")
        with_id = cursor.fetchone()['with_id']
        
        cursor.execute("SELECT COUNT(*) as with_pipe FROM webhooks WHERE user_info LIKE '%|%'")
        with_pipe = cursor.fetchone()['with_pipe']
        
        cursor.execute("SELECT user_info, COUNT(*) as count FROM webhooks WHERE user_info IS NOT NULL GROUP BY user_info LIMIT 10")
        samples = cursor.fetchall()
        
        print(f"\n📊 VERIFICA AGGIORNAMENTI:")
        print(f"  Totale webhook con user_info: {total}")
        print(f"  Con formato ID: {with_id}")
        print(f"  Con formato pipe (|): {with_pipe}")
        
        print(f"\n🔍 Esempi user_info attuali:")
        for sample in samples:
            print(f"  '{sample['user_info']}' ({sample['count']} volte)")
        
    except Exception as e:
        logging.error(f"Errore verifica: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def main():
    print("🔄 Aggiornamento formato utente nei webhook esistenti")
    print("=" * 60)
    
    print("\n📋 Stato attuale:")
    verify_updates()
    
    print(f"\n🚀 Avvio aggiornamento...")
    success = update_existing_webhooks()
    
    if success:
        print(f"\n📋 Stato dopo aggiornamento:")
        verify_updates()
        print(f"\n✅ Aggiornamento completato con successo!")
        print(f"🌐 Ricarica la dashboard per vedere i cambiamenti:")
        print(f"   http://localhost:5000/webhook-manager.html")
    else:
        print(f"\n❌ Aggiornamento fallito")

if __name__ == "__main__":
    main()
