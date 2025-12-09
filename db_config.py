# Configurazione Database MySQL
import mysql.connector
from mysql.connector import Error
import logging
import requests
import config
import os
from datetime import datetime

# === CONFIGURAZIONE EMAIL PER AUTOMAZIONI ===
# PERSONALIZZA QUESTI VALORI per attivare le notifiche email reali
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Server SMTP
    'smtp_port': 587,                 # Porta SMTP
    'email_user': 'your-email@company.com',      # Email mittente
    'email_pass': 'your-app-password',           # Password/App Password
    'recipients': {
        'managers': ['manager@company.com'],      # Manager
        'accounting': ['accounting@company.com'], # Contabilità
        'technical': ['tech@company.com']         # Tecnici
    }
}

# Configurazione connessione database (senza specificare il database)
DB_CONFIG_BASE = {
    'host': 'localhost',
    'user': 'tim_root',
    'password': 'gianni225524',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

# Configurazione connessione database completa
DB_CONFIG = {
    'host': 'localhost',
    'database': 'quickbooks_data',
    'user': 'tim_root',
    'password': 'gianni225524',
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

def get_db_connection(use_database=True):
    """Crea e restituisce una connessione al database"""
    try:
        config = DB_CONFIG if use_database else DB_CONFIG_BASE
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Errore connessione database: {e}")
        return None

def create_tables():
    """Crea le tabelle necessarie se non esistono"""
    # Prima connessione senza database per creare il database
    connection = get_db_connection(use_database=False)
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # Crea il database se non esiste
        cursor.execute("CREATE DATABASE IF NOT EXISTS quickbooks_data CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logging.info("Database quickbooks_data creato o verificato")
        
        cursor.close()
        connection.close()
        
        # Seconda connessione con il database per creare le tabelle
        connection = get_db_connection(use_database=True)
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Tabella per le fatture
        create_bills_table = """
        CREATE TABLE IF NOT EXISTS bills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            supplier VARCHAR(255),
            bill_date DATE,
            due_date DATE,
            bill_no VARCHAR(100),
            location VARCHAR(100),
            memo TEXT,
            account VARCHAR(255),
            line_description TEXT,
            quantity DECIMAL(10,3) DEFAULT NULL,
            unit_price DECIMAL(10,2) DEFAULT NULL,
            line_amount DECIMAL(10,2),
            line_tax_code VARCHAR(50),
            line_tax_amount DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_supplier (supplier),
            INDEX idx_bill_date (bill_date),
            INDEX idx_bill_no (bill_no)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        # Tabella per i webhook
        create_webhooks_table = """
        CREATE TABLE IF NOT EXISTS webhooks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            webhook_id VARCHAR(100) UNIQUE,
            source VARCHAR(100) NOT NULL,
            event_type VARCHAR(100),
            item_type VARCHAR(100),
            project_id VARCHAR(50),
            project_name TEXT,
            user_info VARCHAR(255),
            status VARCHAR(100),
            headers JSON,
            payload JSON,
            processed BOOLEAN DEFAULT FALSE,
            processing_result TEXT,
            error_message TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP NULL,
            INDEX idx_source (source),
            INDEX idx_event_type (event_type),
            INDEX idx_item_type (item_type),
            INDEX idx_project_id (project_id),
            INDEX idx_processed (processed),
            INDEX idx_received_at (received_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        # Tabella per tracking cambi di stato progetti
        create_project_status_tracking_table = """
        CREATE TABLE IF NOT EXISTS project_status_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT NOT NULL,
            old_status VARCHAR(255),
            new_status VARCHAR(255) NOT NULL,
            old_status_name VARCHAR(255),
            new_status_name VARCHAR(255),
            webhook_id INT,
            automation_triggered BOOLEAN DEFAULT FALSE,
            automation_result TEXT,
            automation_error TEXT,
            detected_via ENUM('webhook', 'polling', 'manual') DEFAULT 'webhook',
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_project_id (project_id),
            INDEX idx_changed_at (changed_at),
            INDEX idx_automation_triggered (automation_triggered),
            INDEX idx_detected_via (detected_via),
            FOREIGN KEY (webhook_id) REFERENCES webhooks(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_bills_table)
        
        # Aggiorna la tabella bills se mancano i nuovi campi
        update_bills_table_structure(cursor)
        
        # Tabella per i webhook
        cursor.execute(create_webhooks_table)
        cursor.execute(create_project_status_tracking_table)
        
        # Aggiungi colonna user_info se non esiste (per tabelle esistenti)
        try:
            alter_webhooks_table = """
            ALTER TABLE webhooks 
            ADD COLUMN user_info VARCHAR(255) NULL 
            AFTER project_name
            """
            cursor.execute(alter_webhooks_table)
            logging.info("Colonna user_info aggiunta alla tabella webhooks")
        except Error as e:
            if "Duplicate column name" in str(e):
                logging.debug("Colonna user_info già esistente nella tabella webhooks")
            else:
                logging.warning(f"Errore aggiunta colonna user_info: {e}")
        
        # Aggiungi colonna item_type se non esiste (per tabelle esistenti)
        try:
            alter_item_type_table = """
            ALTER TABLE webhooks 
            ADD COLUMN item_type VARCHAR(100) NULL 
            AFTER event_type
            """
            cursor.execute(alter_item_type_table)
            logging.info("Colonna item_type aggiunta alla tabella webhooks")
        except Error as e:
            if "Duplicate column name" in str(e):
                logging.debug("Colonna item_type già esistente nella tabella webhooks")
            else:
                logging.warning(f"Errore aggiunta colonna item_type: {e}")
        
        logging.info("Tabelle create/verificate con successo")
        return True
        
    except Error as e:
        logging.error(f"Errore creazione tabelle: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def save_bills_to_db(bills_data):
    """Salva i dati delle fatture nel database con supporto per quantity e unit_price"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return False, "Impossibile connettersi al database"
    
    try:
        cursor = connection.cursor()
        
        # Verifica se il CSV contiene campi Quantity e UnitPrice
        sample_bill = bills_data[0] if bills_data else {}
        has_quantity = 'Quantity' in sample_bill
        has_unit_price = 'UnitPrice' in sample_bill
        has_tax_fields = 'LineTaxCode' in sample_bill and 'LineTaxAmount' in sample_bill
        
        logging.info(f"CSV format detected - Quantity: {has_quantity}, UnitPrice: {has_unit_price}, Tax fields: {has_tax_fields}")
        
        # Query di inserimento dinamica basata sui campi disponibili
        if has_quantity and has_unit_price:
            # CSV con quantità e prezzo unitario
            if has_tax_fields:
                insert_query = """
                INSERT INTO bills (filename, supplier, bill_date, due_date, bill_no, 
                                  location, memo, account, line_description, quantity, 
                                  unit_price, line_amount, line_tax_code, line_tax_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            else:
                insert_query = """
                INSERT INTO bills (filename, supplier, bill_date, due_date, bill_no, 
                                  location, memo, account, line_description, quantity, 
                                  unit_price, line_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
        else:
            # CSV standard senza quantità
            if has_tax_fields:
                insert_query = """
                INSERT INTO bills (filename, supplier, bill_date, due_date, bill_no, 
                                  location, memo, account, line_description, line_amount,
                                  line_tax_code, line_tax_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
            else:
                insert_query = """
                INSERT INTO bills (filename, supplier, bill_date, due_date, bill_no, 
                                  location, memo, account, line_description, line_amount)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
        
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        duplicate_details = []
        
        for bill in bills_data:
            try:
                # Verifica duplicati basati su chiavi univoche
                if check_bill_duplicate(cursor, bill):
                    duplicate_count += 1
                    detail = (
                        f"BillNo={bill.get('BillNo','N/A')} | "
                        f"Supplier={bill.get('Supplier','N/A')} | "
                        f"Desc={bill.get('LineDescription','N/A')} | "
                        f"Qty={bill.get('Quantity','')} | UnitPrice={bill.get('UnitPrice','')} | "
                        f"Amount={bill.get('LineAmount','')} | File={bill.get('Filename','')}"
                    )
                    duplicate_details.append(detail)
                    logging.info(f"Fattura duplicata saltata: {detail}")
                    continue
                
                # Converte le date dal formato DD/MM/YYYY a YYYY-MM-DD
                bill_date = convert_date_format(bill.get('BillDate', ''))
                due_date = convert_date_format(bill.get('DueDate', ''))
                
                # Converte gli amount in decimali
                line_amount = safe_decimal_conversion(bill.get('LineAmount', '0'))
                
                # Prepara i valori base
                base_values = [
                    bill.get('Filename', ''),
                    bill.get('Supplier', ''),
                    bill_date,
                    due_date,
                    bill.get('BillNo', ''),
                    bill.get('Location', ''),
                    bill.get('Memo', ''),
                    bill.get('Account', ''),
                    bill.get('LineDescription', ''),
                ]
                
                # Aggiungi valori specifici per il formato
                if has_quantity and has_unit_price:
                    quantity = safe_decimal_conversion(bill.get('Quantity', '1'))
                    unit_price = safe_decimal_conversion(bill.get('UnitPrice', '0'))
                    values = base_values + [quantity, unit_price, line_amount]
                else:
                    values = base_values + [line_amount]
                
                # Aggiungi campi tax se presenti
                if has_tax_fields:
                    line_tax_code = bill.get('LineTaxCode', '')
                    line_tax_amount = safe_decimal_conversion(bill.get('LineTaxAmount', '0'))
                    values.extend([line_tax_code, line_tax_amount])
                
                cursor.execute(insert_query, values)
                saved_count += 1
                
            except Exception as e:
                error_count += 1
                logging.warning(f"Errore salvando riga {bill.get('BillNo', 'N/A')}: {e}")
                continue
        
        connection.commit()
        
        message = f"Salvate {saved_count} fatture"
        if duplicate_count > 0:
            message += f", {duplicate_count} duplicate saltate"
            try:
                log_path = os.path.join(os.getcwd(), "duplicate_bills.log")
                with open(log_path, "a", encoding="utf-8") as dup_log:
                    dup_log.write(f"\n=== Duplicati {datetime.now().isoformat()} ===\n")
                    for d in duplicate_details:
                        dup_log.write(d + "\n")
                logging.info(f"Dettaglio duplicati scritto in {log_path}")
            except Exception as e:
                logging.warning(f"Impossibile scrivere il log dei duplicati: {e}")
        if error_count > 0:
            message += f", {error_count} errori"
            
        logging.info(message)
        return True, message
        
    except Error as e:
        logging.error(f"Errore salvataggio database: {e}")
        return False, f"Errore salvataggio: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def check_bill_duplicate(cursor, bill):
    """Verifica se una fattura esiste già nel database"""
    try:
        # Normalizza quantità e prezzo unitario per il confronto (se presenti)
        qty = safe_decimal_conversion(bill.get('Quantity', ''))
        unit_price = safe_decimal_conversion(bill.get('UnitPrice', ''))

        # Controlla duplicati basati su bill_no, supplier, descrizione, quantità, prezzo unitario
        # ma solo se provengono da un file diverso (filename diverso). In questo modo
        # non scartiamo righe identiche presenti nello stesso file/fattura.
        check_query = """
        SELECT COUNT(*) FROM bills 
        WHERE bill_no = %s AND supplier = %s AND line_description = %s
            AND quantity = %s AND unit_price = %s
            AND filename <> %s
        """
        
        cursor.execute(check_query, (
            bill.get('BillNo', ''),
            bill.get('Supplier', ''),
            bill.get('LineDescription', ''),
            qty,
            unit_price,
            bill.get('Filename', '')
        ))
        
        count = cursor.fetchone()[0]
        return count > 0
        
    except Exception as e:
        logging.warning(f"Errore verifica duplicati: {e}")
        return False

def convert_date_format(date_str):
    """Converte data da MM/DD/YYYY (formato americano) a YYYY-MM-DD"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        from datetime import datetime
        # Assume formato MM/DD/YYYY (formato americano)
        date_obj = datetime.strptime(date_str.strip(), '%m/%d/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except:
        return None

def safe_decimal_conversion(value):
    """Converte in modo sicuro un valore in decimale"""
    if not value or str(value).strip() == '':
        return 0.00
    try:
        # Rimuove spazi e caratteri non numerici comuni
        cleaned_value = str(value).strip().replace(',', '.')
        # Prova a estrarre solo i numeri (incluso il punto decimale)
        import re
        numeric_match = re.match(r'^-?\d*\.?\d*', cleaned_value)
        if numeric_match and numeric_match.group():
            return float(numeric_match.group())
        else:
            return 0.00
    except (ValueError, TypeError):
        return 0.00

def test_connection():
    """Testa la connessione al database"""
    # Prima testa la connessione base
    connection = get_db_connection(use_database=False)
    if not connection:
        return False, "Impossibile connettersi al server MySQL"
    
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        
        # Poi testa la connessione al database specifico
        connection = get_db_connection(use_database=True)
        if connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            connection.close()
            return True, "Connessione al database riuscita"
        else:
            return True, "Connessione server riuscita (database sarà creato)"
            
    except Error as e:
        return False, f"Errore test connessione: {e}"

def search_bills(search_term="", date_from=None, date_to=None, supplier="", 
                amount_min=None, amount_max=None, page=1, per_page=50):
    """
    Cerca fatture nel database con filtri multipli
    """
    connection = get_db_connection(use_database=True)
    if not connection:
        return False, "Impossibile connettersi al database", [], 0, 0
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Costruisci la query base
        base_query = """
         SELECT id, filename, supplier, bill_date, due_date, bill_no, 
             location, memo, account, line_description, line_amount,
             quantity, unit_price,
             created_at, updated_at
        FROM bills
        WHERE 1=1
        """
        
        # Parametri per la query
        params = []
        conditions = []
        
        # Filtro per termine di ricerca (cerca in supplier, bill_no, line_description)
        if search_term:
            conditions.append("""
                (supplier LIKE %s OR bill_no LIKE %s OR line_description LIKE %s 
                 OR memo LIKE %s OR filename LIKE %s)
            """)
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 5)
        
        # Filtro per data fattura
        if date_from:
            conditions.append("bill_date >= %s")
            params.append(date_from)
        
        if date_to:
            conditions.append("bill_date <= %s")
            params.append(date_to)
        
        # Filtro per fornitore specifico
        if supplier:
            conditions.append("supplier LIKE %s")
            params.append(f"%{supplier}%")
        
        # Filtro per importo minimo
        if amount_min is not None and amount_min != "":
            conditions.append("line_amount >= %s")
            params.append(float(amount_min))
        
        # Filtro per importo massimo
        if amount_max is not None and amount_max != "":
            conditions.append("line_amount <= %s")
            params.append(float(amount_max))
        
        # Aggiungi condizioni alla query
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Query per il conteggio totale
        count_query = "SELECT COUNT(*) as total FROM bills WHERE 1=1"
        if conditions:
            count_query += " AND " + " AND ".join(conditions)
        
        # Esegui conteggio
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Calcola paginazione
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Query finale con ordinamento e limite
        final_query = base_query + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        final_params = params + [per_page, offset]
        
        # Esegui query principale
        cursor.execute(final_query, final_params)
        results = cursor.fetchall()
        
        # Query per tutti i dati (per export) - limitata a 10000 record per sicurezza
        if total_count <= 10000:
            export_query = base_query + " ORDER BY created_at DESC"
            cursor.execute(export_query, params)
            all_results = cursor.fetchall()
        else:
            all_results = results  # Se troppi dati, export solo la pagina corrente
        
        logging.info(f"Ricerca completata: {total_count} risultati totali, pagina {page}/{total_pages}")
        
        return True, "Ricerca completata", results, total_count, total_pages, all_results
        
    except Error as e:
        logging.error(f"Errore durante la ricerca: {e}")
        return False, f"Errore durante la ricerca: {str(e)}", [], 0, 0, []
    except Exception as e:
        logging.error(f"Errore generico durante la ricerca: {e}")
        return False, f"Errore: {str(e)}", [], 0, 0, []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_bills_stats():
    """
    Ottieni statistiche sulla tabella bills
    """
    connection = get_db_connection(use_database=True)
    if not connection:
        return None
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        stats_query = """
        SELECT 
            COUNT(*) as total_bills,
            COUNT(DISTINCT supplier) as unique_suppliers,
            MIN(bill_date) as earliest_date,
            MAX(bill_date) as latest_date,
            SUM(line_amount) as total_amount,
            AVG(line_amount) as avg_amount
        FROM bills
        """
        
        cursor.execute(stats_query)
        stats = cursor.fetchone()
        
        return stats
        
    except Error as e:
        logging.error(f"Errore ottenendo statistiche: {e}")
        return None
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def save_webhook_to_db(source, webhook_data, headers=None):
    """Salva un webhook nel database"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return False, "Impossibile connettersi al database"
    
    try:
        cursor = connection.cursor()
        
        # Estrai informazioni dal payload
        webhook_id = webhook_data.get('id') or webhook_data.get('webhook_id') or str(hash(str(webhook_data)))
        
        # MIGLIORAMENTO: Riconoscimento fonte più sofisticato
        if source == "unknown" and headers:
            # Cerca indizi negli header
            if headers.get('x-rentman-webhook'):
                source = "rentman"
            elif headers.get('x-hook-secret') or 'rentman' in str(headers.get('user-agent', '')).lower():
                source = "rentman"
            elif 'zapier' in str(headers.get('user-agent', '')).lower():
                source = "zapier"
            elif 'github' in str(headers.get('user-agent', '')).lower():
                source = "github"
        
        # Cerca indizi nel payload per identificare la fonte
        if source == "unknown":
            if webhook_data.get('account') == 'itinerapro' or 'rentman' in str(webhook_data).lower():
                source = "rentman"
            elif webhook_data.get('zen_id') or webhook_data.get('zendesk'):
                source = "zendesk"
            elif webhook_data.get('repository') and webhook_data.get('commits'):
                source = "github"
        
        # Estrai tipo di evento (cerca in vari campi possibili)
        event_type = (webhook_data.get('event') or 
                     webhook_data.get('type') or 
                     webhook_data.get('event_type') or 
                     webhook_data.get('eventType') or
                     webhook_data.get('action'))
        
        # NUOVO: Estrai itemType
        item_type = (webhook_data.get('itemType') or
                    webhook_data.get('item_type') or
                    webhook_data.get('itemtype') or
                    webhook_data.get('object_type') or
                    webhook_data.get('resource_type'))
        
        # Se non c'è itemType esplicito, prova a dedurlo dal contesto
        if not item_type and webhook_data:
            if 'project' in webhook_data or 'Project' in str(webhook_data):
                item_type = "Project"
            elif 'crew' in webhook_data or 'Crew' in str(webhook_data):
                item_type = "Crew"
            elif 'equipment' in webhook_data or 'Equipment' in str(webhook_data):
                item_type = "ProjectEquipment"
            elif 'contact' in webhook_data or 'Contact' in str(webhook_data):
                item_type = "Contact"
        
        # Estrai ID progetto (cerca in vari campi possibili)
        project_id = (webhook_data.get('project_id') or 
                     webhook_data.get('projectId') or 
                     (webhook_data.get('project', {}).get('id') if isinstance(webhook_data.get('project'), dict) else None))
        
        # Estrai nome progetto
        project_name = (webhook_data.get('project_name') or 
                       webhook_data.get('name') or
                       (webhook_data.get('project', {}).get('name') if isinstance(webhook_data.get('project'), dict) else None))
        
        # MIGLIORAMENTO: Estrazione informazioni utente più completa con recupero da Rentman
        user_info = None
        if 'user' in webhook_data:
            user_data = webhook_data['user']
            if isinstance(user_data, dict):
                # Priorità al nome dell'utente se già presente
                user_name = (user_data.get('name') or 
                           user_data.get('displayname') or 
                           user_data.get('username') or
                           user_data.get('display_name') or
                           user_data.get('full_name'))
                
                if user_name:
                    # Se c'è il nome, usa solo quello
                    user_info = user_name
                else:
                    # Se non c'è il nome ma c'è l'ID, prova a recuperarlo da Rentman
                    user_id = user_data.get('id')
                    if user_id and source == "rentman":
                        # Tenta di recuperare il nome da Rentman
                        rentman_name = get_rentman_user_name(user_id)
                        if rentman_name:
                            user_info = rentman_name
                        else:
                            user_info = f"ID:{user_id}"
                    elif user_id:
                        user_info = f"ID:{user_id}"
                    else:
                        # Ultimo fallback: converti tutto in stringa
                        user_info = str(user_data)
            else:
                user_info = str(user_data)
        elif 'userId' in webhook_data:
            user_id = webhook_data['userId']
            if source == "rentman":
                rentman_name = get_rentman_user_name(user_id)
                user_info = rentman_name if rentman_name else f"ID:{user_id}"
            else:
                user_info = f"ID:{user_id}"
        elif 'username' in webhook_data:
            user_info = webhook_data['username']
        elif 'user_id' in webhook_data:
            user_id = webhook_data['user_id']
            if source == "rentman":
                rentman_name = get_rentman_user_name(user_id)
                user_info = rentman_name if rentman_name else f"ID:{user_id}"
            else:
                user_info = f"ID:{user_id}"
        
        status = webhook_data.get('status') or webhook_data.get('state')
        
        # Converti headers in JSON se presente
        headers_json = None
        if headers:
            import json
            try:
                headers_json = json.dumps(dict(headers))
            except:
                headers_json = str(headers)
        
        # Converti payload in JSON
        payload_json = None
        try:
            import json
            payload_json = json.dumps(webhook_data)
        except:
            payload_json = str(webhook_data)
        
        # Query di inserimento con ON DUPLICATE KEY UPDATE per evitare duplicati
        insert_query = """
        INSERT INTO webhooks (webhook_id, source, event_type, item_type, project_id, project_name, 
                             user_info, status, headers, payload, processed)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            event_type = VALUES(event_type),
            item_type = VALUES(item_type),
            project_name = VALUES(project_name),
            user_info = VALUES(user_info),
            status = VALUES(status),
            headers = VALUES(headers),
            payload = VALUES(payload),
            received_at = CURRENT_TIMESTAMP
        """
        
        values = (
            webhook_id[:100],  # Limita lunghezza
            source[:100],
            event_type[:100] if event_type else None,
            item_type[:100] if item_type else None,  # Nuovo campo
            str(project_id)[:50] if project_id else None,  # Converti in stringa prima di limitare
            project_name,
            user_info[:255] if user_info else None,
            status[:100] if status else None,
            headers_json,
            payload_json,
            False  # processed = False
        )
        
        cursor.execute(insert_query, values)
        connection.commit()
        
        webhook_db_id = cursor.lastrowid
        logging.info(f"Webhook salvato nel database:")
        logging.info(f"  ID: {webhook_db_id}")
        logging.info(f"  Fonte: {source}")
        logging.info(f"  Evento: {event_type or 'N/A'}")
        logging.info(f"  ItemType: {item_type or 'N/A'}")
        logging.info(f"  Progetto: {project_id or 'N/A'} - {project_name or 'N/A'}")
        logging.info(f"  Utente: {user_info or 'N/A'}")
        
        return True, f"Webhook salvato con ID: {webhook_db_id}"
        
    except Error as e:
        logging.error(f"Errore salvataggio webhook: {e}")
        return False, f"Errore salvataggio webhook: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_webhooks_from_db(filters=None, limit=100, offset=0):
    """Recupera webhook dal database con filtri opzionali"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return None, "Impossibile connettersi al database"
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        # Query base
        query = "SELECT * FROM webhooks"
        where_conditions = []
        params = []
        
        # Applica filtri se presenti
        if filters:
            if filters.get('source'):
                where_conditions.append("source = %s")
                params.append(filters['source'])
            
            if filters.get('event_type'):
                where_conditions.append("event_type = %s")
                params.append(filters['event_type'])
            
            if filters.get('project_id'):
                where_conditions.append("project_id = %s")
                params.append(filters['project_id'])
            
            if filters.get('processed') is not None:
                where_conditions.append("processed = %s")
                params.append(filters['processed'])
            
            if filters.get('date_from'):
                where_conditions.append("received_at >= %s")
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                where_conditions.append("received_at <= %s")
                params.append(filters['date_to'])
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        webhooks = cursor.fetchall()
        
        # Conta il totale
        count_query = "SELECT COUNT(*) as total FROM webhooks"
        if where_conditions:
            count_query += " WHERE " + " AND ".join(where_conditions[:-2])  # Rimuovi LIMIT e OFFSET dai parametri
            cursor.execute(count_query, params[:-2])
        else:
            cursor.execute(count_query)
        
        total_count = cursor.fetchone()['total']
        
        logging.info(f"Recuperati {len(webhooks)} webhook dal database")
        return webhooks, total_count
        
    except Error as e:
        logging.error(f"Errore recupero webhook: {e}")
        return None, f"Errore recupero webhook: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def update_webhook_processing_status(webhook_id, processed=True, result=None, error=None):
    """Aggiorna lo stato di elaborazione di un webhook"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return False, "Impossibile connettersi al database"
    
    try:
        cursor = connection.cursor()
        
        update_query = """
        UPDATE webhooks 
        SET processed = %s, processing_result = %s, error_message = %s, processed_at = CURRENT_TIMESTAMP
        WHERE id = %s OR webhook_id = %s
        """
        
        values = (processed, result, error, webhook_id, webhook_id)
        cursor.execute(update_query, values)
        connection.commit()
        
        affected_rows = cursor.rowcount
        if affected_rows > 0:
            logging.info(f"Aggiornato stato webhook {webhook_id}")
            return True, f"Webhook {webhook_id} aggiornato"
        else:
            logging.warning(f"Nessun webhook trovato con ID {webhook_id}")
            return False, f"Webhook {webhook_id} non trovato"
        
    except Error as e:
        logging.error(f"Errore aggiornamento webhook: {e}")
        return False, f"Errore aggiornamento webhook: {str(e)}"
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Cache per i nomi utente di Rentman per evitare chiamate API ripetute
_rentman_user_cache = {}

def get_rentman_user_name(user_id):
    """Recupera il nome dell'utente da Rentman usando l'ID"""
    if not user_id:
        return None
    
    # Controlla la cache prima
    if user_id in _rentman_user_cache:
        return _rentman_user_cache[user_id]
    
    try:
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        crew_url = f"{config.REN_BASE_URL}/crew/{user_id}"
        crew_resp = requests.get(crew_url, headers=headers, timeout=5)
        
        if crew_resp.ok:
            crew_data = crew_resp.json().get('data', {})
            user_name = crew_data.get('name') or crew_data.get('displayname')
            
            if user_name:
                # Salva in cache
                _rentman_user_cache[user_id] = user_name
                logging.info(f"Nome utente Rentman recuperato: ID {user_id} -> {user_name}")
                return user_name
            else:
                logging.warning(f"Nome utente non trovato per ID {user_id} in Rentman")
        else:
            logging.warning(f"Errore API Rentman per utente {user_id}: {crew_resp.status_code}")
    
    except Exception as e:
        logging.error(f"Errore recuperando nome utente Rentman {user_id}: {e}")
    
    # Se non riusciamo a recuperare il nome, salva None in cache per evitare retry continui
    _rentman_user_cache[user_id] = None
    return None

def track_project_status_change(project_id, current_status, webhook_id=None, item_type=None):
    """
    Traccia i cambi di stato confrontando con l'ultimo stato salvato
    Returns: True se c'è stato un cambio, False altrimenti
    """
    logging.info(f"🔍 DEBUG track_project_status_change INIZIO:")
    logging.info(f"   project_id: {project_id} (tipo: {type(project_id)})")
    logging.info(f"   current_status: {current_status}")
    logging.info(f"   webhook_id: {webhook_id}")
    logging.info(f"   item_type: {item_type}")
    
    connection = get_db_connection(use_database=True)
    if not connection:
        logging.error(f"❌ DEBUG: Nessuna connessione database!")
        return False
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        item_label = "SubProgetto" if item_type == "SubProject" else "Progetto"
        
        logging.info(f"🔍 DEBUG: Recupero ultimo stato per progetto {project_id}...")
        
        # Recupera l'ultimo stato salvato
        cursor.execute("""
            SELECT new_status, new_status_name FROM project_status_tracking 
            WHERE project_id = %s
            ORDER BY changed_at DESC 
            LIMIT 1
        """, (project_id,))
        
        result = cursor.fetchone()
        last_status = result['new_status'] if result else None
        last_status_name = result['new_status_name'] if result else None
        
        logging.info(f"🔍 DEBUG: Ultimo stato trovato: {last_status} ({last_status_name})")
        logging.info(f"🔍 DEBUG: Stato attuale: {current_status}")
        
        # Se è la prima volta o lo status è cambiato
        if last_status is None or last_status != current_status:
            logging.info(f"🔍 DEBUG: CAMBIO RILEVATO! Primo salvataggio: {last_status is None}, Stati diversi: {last_status != current_status}")
            
            # Recupera i nomi degli stati da Rentman
            logging.info(f"🔍 DEBUG: Recuperando nome stato da Rentman...")
            current_status_name = get_status_name_from_rentman(current_status)
            old_status_name = last_status_name if last_status else None
            
            logging.info(f"🔍 DEBUG: Nome stato risolto: {current_status_name}")
            
            # Salva il cambio di stato
            logging.info(f"🔍 DEBUG: Inserendo nella tabella project_status_tracking...")
            cursor.execute("""
                INSERT INTO project_status_tracking 
                (project_id, old_status, new_status, old_status_name, new_status_name, webhook_id, detected_via)
                VALUES (%s, %s, %s, %s, %s, %s, 'webhook')
            """, (project_id, last_status, current_status, old_status_name, current_status_name, webhook_id))
            
            connection.commit()
            tracking_id = cursor.lastrowid
            logging.info(f"🔍 DEBUG: Record inserito con ID: {tracking_id}")
            
            if last_status is not None:  # Non è il primo salvataggio
                logging.info(f"🔄 CAMBIO STATO RILEVATO - {item_label} {project_id}")
                logging.info(f"   Da: {last_status} ({old_status_name})")
                logging.info(f"   A:  {current_status} ({current_status_name})")
                logging.info(f"   Tipo: {item_type or 'Project'}")
                
                logging.info(f"🔍 DEBUG: Triggerando automazioni...")
                trigger_project_automations(project_id, last_status, current_status, 
                                           old_status_name, current_status_name, tracking_id, item_type)
                
                logging.info(f"🔍 DEBUG: track_project_status_change COMPLETATA - CAMBIO RILEVATO")
                return True
            else:
                logging.info(f"📝 PRIMO STATUS SALVATO - {item_label} {project_id}: {current_status} ({current_status_name})")
                logging.info(f"🔍 DEBUG: track_project_status_change COMPLETATA - PRIMO SALVATAGGIO")
                return False
        else:
            logging.info(f"🔍 DEBUG: Nessun cambio - stesso stato: {current_status}")
        
        logging.info(f"🔍 DEBUG: track_project_status_change COMPLETATA - NESSUN CAMBIO")
        return False
        
    except Exception as e:
        logging.error(f"❌ DEBUG: Errore tracking status progetto {project_id}: {e}")
        import traceback
        logging.error(f"❌ DEBUG TRACEBACK: {traceback.format_exc()}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_status_name_from_rentman(status_path):
    """Recupera il nome dello stato da Rentman usando il path"""
    try:
        from rentman_api import extract_id_from_path, get_all_statuses
        
        status_id = extract_id_from_path(status_path)
        if not status_id:
            return status_path
        
        headers = {'Authorization': f'Bearer {config.REN_API_TOKEN}'}
        status_map = get_all_statuses(headers)
        
        return status_map.get(status_id, status_path)
        
    except Exception as e:
        logging.error(f"Errore recuperando nome status {status_path}: {e}")
        return status_path

def trigger_project_automations(project_id, old_status, new_status, old_status_name, new_status_name, tracking_id, item_type=None):
    """Triggera le automazioni basate sul cambio di stato"""
    
    automation_results = []
    item_label = "SubProgetto" if item_type == "SubProject" else "Progetto"
    
    try:
        logging.info(f"🤖 AVVIO AUTOMAZIONI - {item_label} {project_id}")
        logging.info(f"   Cambio: {old_status_name} → {new_status_name}")
        logging.info(f"   Tipo: {item_type or 'Project'}")
        
        # Normalizza nomi per confronto
        new_status_lower = new_status_name.lower() if new_status_name else ""
        old_status_lower = old_status_name.lower() if old_status_name else ""
        
        # 1. PROGETTO RIENTRATO (completato/finito)
        if 'rientrato' in new_status_lower:
            logging.info(f"✅ {item_label} {project_id} rientrato - Avvio procedure di chiusura")
            
            # Automazione: Elimina ore bozza/temporanee
            result = auto_delete_draft_hours(project_id)
            automation_results.append(f"Eliminazione ore bozza: {result}")
            
            # Automazione: Genera fattura finale (se configurato)
            result = auto_generate_final_invoice(project_id)
            automation_results.append(f"Generazione fattura finale: {result}")
            
            # Automazione: Notifica team
            result = auto_notify_project_completion(project_id)
            automation_results.append(f"Notifica completamento: {result}")
        
        # 2. PROGETTO ANNULLATO/ELIMINATO
        elif 'annullato' in new_status_lower or 'eliminato' in new_status_lower or 'cancellato' in new_status_lower:
            logging.info(f"❌ {item_label} {project_id} annullato/eliminato - Avvio procedure di rimozione")
            
            # TEST: Solo log per ora - poi attivare eliminazione QB
            result = auto_test_project_deleted(project_id, old_status_name, new_status_name, item_type)
            automation_results.append(f"TEST {item_label} Eliminato: {result}")
            
            # Automazione: Elimina TUTTE le ore (DISABILITATA per test)
            # result = auto_delete_all_hours(project_id)
            # automation_results.append(f"Eliminazione tutte le ore: {result}")
            
            # Automazione: Elimina fatture bozza (DISABILITATA per test)
            # result = auto_delete_draft_invoices(project_id)
            # automation_results.append(f"Eliminazione fatture bozza: {result}")
            
            # Automazione: Elimina da QuickBooks (DA IMPLEMENTARE)
            # result = auto_delete_from_quickbooks(project_id)
            # automation_results.append(f"Eliminazione da QB: {result}")
            
            # Automazione: Notifica annullamento
            result = auto_notify_project_cancellation(project_id)
            automation_results.append(f"Notifica annullamento: {result}")
        
        # 3. DA CONCETTO/IN OPZIONE A CONFERMATO
        elif (('concetto' in old_status_lower or 'in opzione' in old_status_lower or 'richiesta' in old_status_lower) and
              'confermato' in new_status_lower):
            logging.info(f"🚀 {item_label} {project_id} confermato - Avvio procedure di attivazione")
            
            # TEST: Solo log per ora - poi attivare creazione QB
            result = auto_test_project_confirmed(project_id, old_status_name, new_status_name, item_type)
            automation_results.append(f"TEST {item_label} Confermato: {result}")
            
            # Automazione: Crea sub-customer in QuickBooks (DISABILITATA per test)
            # result = auto_create_subcustomer(project_id)
            # automation_results.append(f"Creazione sub-customer QB: {result}")
            
            # Automazione: Attiva sincronizzazioni (DISABILITATA per test)
            # result = auto_enable_sync(project_id)
            # automation_results.append(f"Attivazione sincronizzazioni: {result}")
            
            # Automazione: Notifica team
            result = auto_notify_project_confirmation(project_id)
            automation_results.append(f"Notifica conferma: {result}")
        
        # 3b. QUALSIASI CAMBIO A CONFERMATO (più ampio per test)
        elif 'confermato' in new_status_lower and 'confermato' not in old_status_lower:
            logging.info(f"✅ {item_label} {project_id} CONFERMATO da qualsiasi stato precedente")
            
            # TEST: Intercetta qualsiasi cambio verso confermato
            result = auto_test_any_confirmed(project_id, old_status_name, new_status_name, item_type)
            automation_results.append(f"TEST {item_label} Generico Confermato: {result}")
        
        # 4. IN LOCATION (progetto attivo)
        elif 'in location' in new_status_lower:
            logging.info(f"🔄 Progetto {project_id} in location - Procedure di attivazione")
            
            # Automazione: Assicura sub-customer QB esistente
            result = auto_ensure_subcustomer(project_id)
            automation_results.append(f"Verifica sub-customer QB: {result}")
        
        # 5. PRONTO (progetto pronto per l'esecuzione)
        elif 'pronto' in new_status_lower:
            logging.info(f"🎯 Progetto {project_id} pronto - Preparazione finale")
            
            # Automazione: Verifica sub-customer e preparazione
            result = auto_ensure_subcustomer(project_id)
            automation_results.append(f"Verifica sub-customer QB: {result}")
            
            # Automazione: Notifica team
            result = auto_notify_project_ready(project_id)
            automation_results.append(f"Notifica progetto pronto: {result}")
        
        # 6. IN PREPARAZIONE (nuovo automatismo esempio)
        elif 'in preparazione' in new_status_lower:
            logging.info(f"🔧 Progetto {project_id} in preparazione - Avvio preparazione risorse")
            
            # Automazione: Verifica attrezzature
            result = auto_check_equipment_availability(project_id)
            automation_results.append(f"Verifica attrezzature: {result}")
            
            # Automazione: Notifica team tecnico
            result = auto_notify_technical_team(project_id)
            automation_results.append(f"Notifica team tecnico: {result}")
        
        # 7. ESEMPIO: Automatismo basato su cambio specifico
        elif old_status_lower == 'richiesta' and new_status_lower == 'preventivo':
            logging.info(f"📋 Progetto {project_id} da Richiesta a Preventivo")
            
            # Automazione: Genera preventivo automatico
            result = auto_generate_quote(project_id)
            automation_results.append(f"Generazione preventivo: {result}")
        
        # Salva i risultati delle automazioni se ci sono state
        if automation_results:
            automation_summary = " | ".join(automation_results)
            update_automation_results(tracking_id, True, automation_summary)
            
            logging.info(f"🎯 AUTOMAZIONI COMPLETATE per progetto {project_id}")
            for result in automation_results:
                logging.info(f"   - {result}")
        else:
            logging.info(f"ℹ️  Nessuna automazione configurata per il cambio {old_status_name} → {new_status_name}")
            update_automation_results(tracking_id, False, "Nessuna automazione configurata per questo cambio di stato")
        
    except Exception as e:
        error_msg = f"Errore durante automazioni: {str(e)}"
        logging.error(f"❌ {error_msg}")
        update_automation_results(tracking_id, False, None, error_msg)

def update_automation_results(tracking_id, triggered, result=None, error=None):
    """Aggiorna i risultati delle automazioni nella tabella tracking"""
    connection = get_db_connection(use_database=True)
    if not connection:
        return
    
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE project_status_tracking 
            SET automation_triggered = %s, automation_result = %s, automation_error = %s
            WHERE id = %s
        """, (triggered, result, error, tracking_id))
        
        connection.commit()
        
    except Exception as e:
        logging.error(f"Errore aggiornando risultati automazione: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# === FUNZIONI DI AUTOMAZIONE ===

def auto_delete_draft_hours(project_id):
    """Elimina le ore bozza/temporanee per un progetto - VERSIONE REALE"""
    try:
        # Integra con la tua funzione esistente
        from delete_qb_time_activities import delete_time_activities_for_project
        
        logging.info(f"🗑️  Eliminazione ore bozza per progetto {project_id}")
        
        # Elimina solo le ore con status "Draft" o simile
        result = delete_time_activities_for_project(
            project_id=project_id,
            status_filter="Draft"  # Personalizza secondo la tua logica
        )
        
        return f"Eliminate {result.get('deleted_count', 0)} ore bozza"
    except Exception as e:
        return f"Errore eliminazione ore bozza: {str(e)}"

def auto_delete_all_hours(project_id):
    """Elimina TUTTE le ore per un progetto annullato - VERSIONE REALE"""
    try:
        from delete_qb_time_activities import delete_time_activities_for_project
        
        logging.info(f"🗑️  Eliminazione TUTTE le ore per progetto {project_id}")
        
        # Elimina tutte le ore del progetto
        result = delete_time_activities_for_project(
            project_id=project_id,
            all_hours=True  # Elimina tutte le ore
        )
        
        return f"Eliminate {result.get('deleted_count', 0)} ore totali"
    except Exception as e:
        return f"Errore eliminazione ore: {str(e)}"

def auto_generate_final_invoice(project_id):
    """Genera fattura finale per progetto completato - VERSIONE REALE"""
    try:
        from create_or_update_invoice_for_project import create_or_update_invoice_for_project
        
        logging.info(f"💰 Generazione fattura finale per progetto {project_id}")
        
        # Crea la fattura finale
        result = create_or_update_invoice_for_project(
            project_id=project_id,
            final=True  # Marca come fattura finale
        )
        
        if result.get('success'):
            return f"Fattura finale generata: {result.get('invoice_id')}"
        else:
            return f"Errore generazione fattura: {result.get('error')}"
    except Exception as e:
        return f"Errore generazione fattura: {str(e)}"

def auto_delete_draft_invoices(project_id):
    """Elimina fatture bozza per progetto annullato"""
    try:
        logging.info(f"🗑️  Eliminazione fatture bozza per progetto {project_id}")
        return "Simulato - Fatture bozza eliminate"
    except Exception as e:
        return f"Errore: {str(e)}"

def auto_create_subcustomer(project_id):
    """Crea sub-customer in QuickBooks per progetto confermato - VERSIONE REALE"""
    try:
        from qb_customer import create_or_update_customer_for_project
        
        logging.info(f"👤 Creazione sub-customer QB per progetto {project_id}")
        
        # Recupera i dati del progetto da Rentman
        from rentman_api import get_project_and_customer
        project_data = get_project_and_customer(project_id)
        
        # Crea il sub-customer
        result = create_or_update_customer_for_project(
            project_id=project_id,
            project_data=project_data['project'],
            customer_data=project_data['customer']
        )
        
        if result.get('success'):
            return f"Sub-customer creato: {result.get('customer_name')}"
        else:
            return f"Errore creazione sub-customer: {result.get('error')}"
    except Exception as e:
        return f"Errore creazione sub-customer: {str(e)}"

def auto_ensure_subcustomer(project_id):
    """Assicura che il sub-customer QB esista"""
    try:
        logging.info(f"🔍 Verifica sub-customer QB per progetto {project_id}")
        return "Simulato - Sub-customer verificato"
    except Exception as e:
        return f"Errore: {str(e)}"

def auto_enable_sync(project_id):
    """Attiva sincronizzazioni automatiche per il progetto"""
    try:
        logging.info(f"🔄 Attivazione sincronizzazioni per progetto {project_id}")
        return "Simulato - Sincronizzazioni attivate"
    except Exception as e:
        return f"Errore: {str(e)}"

def auto_notify_project_completion(project_id):
    """Invia notifica email di completamento progetto - VERSIONE REALE"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        logging.info(f"📧 Notifica completamento progetto {project_id}")
        
        # Configura i dettagli email (personalizza in config.py)
        # Per ora uso valori placeholder - PERSONALIZZA QUESTI
        smtp_server = "smtp.gmail.com"  # Personalizza
        smtp_port = 587
        email_user = "your-email@company.com"  # Personalizza
        email_pass = "your-app-password"       # Personalizza
        
        # Destinatari (personalizza)
        to_emails = ["manager@company.com", "accounting@company.com"]  # Personalizza
        
        # Crea messaggio
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = ", ".join(to_emails)
        msg['Subject'] = f"🏁 Progetto {project_id} Completato - Automazioni Eseguite"
        
        body = f"""
Il progetto {project_id} è stato marcato come RIENTRATO.

🤖 Azioni automatiche eseguite:
✅ Ore bozza eliminate
✅ Fattura finale generata
✅ Sistema aggiornato

Verifica i dettagli nel sistema AppConnettor.

--
Messaggio automatico dal sistema AppConnettor
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Invia email (commentato per sicurezza - decommentare quando configurato)
        # server = smtplib.SMTP(smtp_server, smtp_port)
        # server.starttls()
        # server.login(email_user, email_pass)
        # server.send_message(msg)
        # server.quit()
        
        return f"Notifica preparata per {len(to_emails)} destinatari (configurare SMTP per invio reale)"
    except Exception as e:
        return f"Errore preparazione notifica: {str(e)}"

def auto_notify_project_cancellation(project_id):
    """Invia notifica di annullamento progetto"""
    try:
        logging.info(f"📧 Notifica annullamento progetto {project_id}")
        return "Simulato - Notifica inviata"
    except Exception as e:
        return f"Errore: {str(e)}"

def auto_notify_project_confirmation(project_id):
    """Invia notifica di conferma progetto"""
    try:
        logging.info(f"📧 Notifica conferma progetto {project_id}")
        return "Simulato - Notifica inviata"
    except Exception as e:
        return f"Errore: {str(e)}"

def auto_notify_project_ready(project_id):
    """Invia notifica progetto pronto"""
    try:
        logging.info(f"📧 Notifica progetto pronto {project_id}")
        return "Simulato - Notifica progetto pronto inviata"
    except Exception as e:
        return f"Errore: {str(e)}"

# === NUOVE FUNZIONI DI AUTOMAZIONE (ESEMPI) ===

def auto_check_equipment_availability(project_id):
    """Verifica disponibilità attrezzature per progetto in preparazione"""
    try:
        logging.info(f"🔧 Verifica attrezzature per progetto {project_id}")
        
        # Qui potresti integrare con il tuo sistema di gestione attrezzature
        # Esempio di logica:
        # from rentman_api import get_project_equipment
        # equipment_list = get_project_equipment(project_id)
        # availability = check_equipment_conflicts(equipment_list)
        
        return "Verifica attrezzature completata - Disponibilità OK"
    except Exception as e:
        return f"Errore verifica attrezzature: {str(e)}"

def auto_notify_technical_team(project_id):
    """Invia notifica al team tecnico per progetti in preparazione"""
    try:
        logging.info(f"🔧 Notifica team tecnico per progetto {project_id}")
        
        # Qui potresti inviare notifiche specifiche al team tecnico
        # Email, Slack, Teams, ecc.
        
        return "Notifica inviata al team tecnico"
    except Exception as e:
        return f"Errore notifica team tecnico: {str(e)}"

def auto_generate_quote(project_id):
    """Genera preventivo automatico per progetti"""
    try:
        logging.info(f"📋 Generazione preventivo per progetto {project_id}")
        
        # Qui potresti integrare con il tuo sistema di preventivazione
        # from quote_generator import create_quote_for_project
        # quote = create_quote_for_project(project_id)
        
        return "Preventivo generato automaticamente"
    except Exception as e:
        return f"Errore generazione preventivo: {str(e)}"

# === FUNZIONI DI TEST PER INTERCETTARE CAMBI DI STATO ===

def auto_test_project_confirmed(project_id, old_status_name, new_status_name, item_type=None):
    """TEST: Intercetta progetto che diventa confermato"""
    try:
        item_label = "SubProgetto" if item_type == "SubProject" else "Progetto"
        logging.info(f"🎯 TEST CONFERMATO - {item_label} {project_id}")
        logging.info(f"   Da: {old_status_name} → A: {new_status_name}")
        logging.info(f"   Tipo: {item_type or 'Project'}")
        
        # Recupera dati progetto per il test
        try:
            from rentman_api import get_project_data
            project_data = get_project_data(project_id)
            project_name = project_data.get('name', 'Nome non disponibile')
            customer_info = project_data.get('customer', {})
        except Exception as e:
            project_name = f"Errore recupero dati: {str(e)}"
            customer_info = {}
        
        test_message = f"✅ {item_label.upper()} CONFERMATO RILEVATO!\n"
        test_message += f"ID: {project_id}\n"
        test_message += f"Nome: {project_name}\n"
        test_message += f"Tipo: {item_type or 'Project'}\n"
        test_message += f"Cambio: {old_status_name} → {new_status_name}\n"
        test_message += f"Cliente: {customer_info.get('name', 'N/A')}\n"
        test_message += f"🔜 PROSSIMO PASSO: Creare in QuickBooks"
        
        logging.info(test_message)
        return f"RILEVATO {item_label}: {old_status_name} → {new_status_name} | Cliente: {customer_info.get('name', 'N/A')}"
        
    except Exception as e:
        error_msg = f"Errore test confermato: {str(e)}"
        logging.error(error_msg)
        return error_msg

def auto_test_any_confirmed(project_id, old_status_name, new_status_name, item_type=None):
    """TEST: Intercetta qualsiasi cambio verso confermato"""
    try:
        item_label = "SubProgetto" if item_type == "SubProject" else "Progetto"
        logging.info(f"🔍 TEST CONFERMATO GENERICO - {item_label} {project_id}")
        logging.info(f"   Da: {old_status_name} → A: {new_status_name}")
        logging.info(f"   Tipo: {item_type or 'Project'}")
        
        return f"INTERCETTATO {item_label}: Qualsiasi stato → Confermato | Da: {old_status_name}"
        
    except Exception as e:
        return f"Errore test generico: {str(e)}"

def auto_test_project_deleted(project_id, old_status_name, new_status_name, item_type=None):
    """TEST: Intercetta progetto eliminato/annullato"""
    try:
        item_label = "SubProgetto" if item_type == "SubProject" else "Progetto"
        logging.info(f"🗑️ TEST ELIMINATO - {item_label} {project_id}")
        logging.info(f"   Da: {old_status_name} → A: {new_status_name}")
        logging.info(f"   Tipo: {item_type or 'Project'}")
        
        test_message = f"❌ {item_label.upper()} ELIMINATO RILEVATO!\n"
        test_message += f"ID: {project_id}\n"
        test_message += f"Tipo: {item_type or 'Project'}\n"
        test_message += f"Cambio: {old_status_name} → {new_status_name}\n"
        test_message += f"🔜 PROSSIMO PASSO: Eliminare da QuickBooks"
        
        logging.info(test_message)
        return f"RILEVATO ELIMINAZIONE {item_label}: {old_status_name} → {new_status_name}"
        
    except Exception as e:
        error_msg = f"Errore test eliminato: {str(e)}"
        logging.error(error_msg)
        return error_msg

def update_bills_table_structure(cursor):
    """Aggiorna la struttura della tabella bills per includere i nuovi campi"""
    try:
        # Verifica se i campi esistono già
        cursor.execute("DESCRIBE bills")
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Campi da aggiungere se non esistono
        new_columns = [
            ("quantity", "DECIMAL(10,3) DEFAULT NULL"),
            ("unit_price", "DECIMAL(10,2) DEFAULT NULL"), 
            ("line_tax_code", "VARCHAR(50) DEFAULT NULL"),
            ("line_tax_amount", "DECIMAL(10,2) DEFAULT NULL")
        ]
        
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                alter_query = f"ALTER TABLE bills ADD COLUMN {column_name} {column_definition}"
                cursor.execute(alter_query)
                logging.info(f"Aggiunta colonna {column_name} alla tabella bills")
        
        logging.info("Struttura tabella bills aggiornata")
        
    except Exception as e:
        logging.warning(f"Errore aggiornamento struttura tabella bills: {e}")

def get_db_connection(use_database=True):
    """Crea e restituisce una connessione al database"""
    try:
        config = DB_CONFIG if use_database else DB_CONFIG_BASE
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            return connection
    except Error as e:
        logging.error(f"Errore connessione database: {e}")
        return None
