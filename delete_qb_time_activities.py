#!/usr/bin/env python3
"""
Script per eliminare TimeActivity (ore lavorate) da QuickBooks
Supporta eliminazione per:
- Customer ID
- Nome Progetto (cerca automaticamente nel nome dei Customer)
- Employee Name
- Data specifica
- Intervallo di date
- Tutto (con conferma)

ESEMPI DI USO:
# Anteprima per progetto specifico
python delete_qb_time_activities.py --project-name "Evento Milano" --preview

# Ricerca fuzzy per trovare progetti simili
python delete_qb_time_activities.py --project-name "Milano" --fuzzy-search

# Elimina ore di un employee per un progetto specifico
python delete_qb_time_activities.py --project-name "Evento Milano" --employee "Mario Rossi" --force

# Elimina ore degli ultimi 7 giorni per un progetto
python delete_qb_time_activities.py --project-name "Evento Milano" --last-days 7 --preview
"""

import requests
import config
from token_manager import token_manager
import logging
import sys
from datetime import datetime, timedelta
import argparse

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def init_quickbooks_connection():
    """Inizializza la connessione a QuickBooks"""
    try:
        token_manager.load_refresh_token()
        access_token = token_manager.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            logging.error("Token QuickBooks non valido. Aggiorna il token prima di continuare.")
            return None
            
        return access_token
    except Exception as e:
        logging.error(f"Errore inizializzazione QuickBooks: {e}")
        return None

def get_time_activities(access_token, filters=None):
    """Recupera le TimeActivity da QuickBooks con filtri opzionali"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Costruisci query base
    query = "SELECT * FROM TimeActivity"
    where_conditions = []
    
    if filters:
        if filters.get('customer_id'):
            where_conditions.append(f"CustomerRef = '{filters['customer_id']}'")
        
        if filters.get('project_name'):
            # Trova Customer ID per nome progetto
            customer_id = find_customer_by_project_name(access_token, filters['project_name'])
            if customer_id:
                where_conditions.append(f"CustomerRef = '{customer_id}'")
                logging.info(f"Filtro per progetto '{filters['project_name']}' -> Customer ID: {customer_id}")
            else:
                logging.warning(f"Progetto '{filters['project_name']}' non trovato")
                # Prova ricerca fuzzy
                fuzzy_matches = find_customers_by_project_name_fuzzy(access_token, filters['project_name'])
                if fuzzy_matches:
                    logging.info(f"Possibili match trovati:")
                    for match in fuzzy_matches[:3]:  # Mostra top 3
                        logging.info(f"  - {match['name']} (similarità: {match['similarity']:.2f})")
                    
                    # Usa il migliore match se ha alta similarità
                    best_match = fuzzy_matches[0]
                    if best_match['similarity'] > 0.7:
                        where_conditions.append(f"CustomerRef = '{best_match['id']}'")
                        logging.info(f"Usato best match: {best_match['name']} (ID: {best_match['id']})")
                    else:
                        logging.warning(f"Nessun match abbastanza preciso trovato per '{filters['project_name']}'")
                        return []
                else:
                    return []
        
        if filters.get('employee_name'):
            # Prima trova l'employee ID
            emp_id = find_employee_by_name(access_token, filters['employee_name'])
            if emp_id:
                where_conditions.append(f"EmployeeRef = '{emp_id}'")
            else:
                logging.warning(f"Employee '{filters['employee_name']}' non trovato")
                return []
        
        if filters.get('date_from'):
            where_conditions.append(f"TxnDate >= '{filters['date_from']}'")
            
        if filters.get('date_to'):
            where_conditions.append(f"TxnDate <= '{filters['date_to']}'")
            
        if filters.get('date_exact'):
            where_conditions.append(f"TxnDate = '{filters['date_exact']}'")
    
    if where_conditions:
        query += " WHERE " + " AND ".join(where_conditions)
    
    query += " ORDER BY TxnDate DESC"
    
    logging.info(f"Query: {query}")
    
    try:
        response = requests.get(url, headers=headers, params={"query": query})
        
        if response.status_code == 200:
            data = response.json()
            activities = data.get("QueryResponse", {}).get("TimeActivity", [])
            
            # Se non è una lista, convertila in lista
            if not isinstance(activities, list):
                activities = [activities] if activities else []
                
            logging.info(f"Trovate {len(activities)} TimeActivity")
            return activities
        else:
            logging.error(f"Errore ricerca TimeActivity: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logging.error(f"Errore durante ricerca: {e}")
        return []

def find_employee_by_name(access_token, employee_name):
    """Trova l'ID di un employee per nome"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM Employee WHERE DisplayName = '{employee_name}'"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params={"query": query})
        if response.status_code == 200:
            data = response.json()
            employees = data.get("QueryResponse", {}).get("Employee", [])
            if employees:
                if not isinstance(employees, list):
                    employees = [employees]
                return employees[0]["Id"]
        return None
    except Exception as e:
        logging.error(f"Errore ricerca employee: {e}")
        return None

def delete_time_activity(access_token, activity):
    """Elimina una singola TimeActivity"""
    activity_id = activity["Id"]
    sync_token = activity["SyncToken"]
    
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/timeactivity?operation=delete"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "Id": activity_id,
        "SyncToken": sync_token
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            logging.info(f"✅ Eliminata TimeActivity ID: {activity_id}")
            return True
        else:
            logging.error(f"❌ Errore eliminazione ID {activity_id}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Errore durante eliminazione ID {activity_id}: {e}")
        return False

def show_activity_details(activities):
    """Mostra i dettagli delle TimeActivity trovate"""
    if not activities:
        print("Nessuna TimeActivity trovata.")
        return
    
    print(f"\n=== TROVATE {len(activities)} TIMEACTIVITY ===")
    print(f"{'ID':<10} {'Data':<12} {'Employee':<20} {'Ore':<8} {'Descrizione':<30}")
    print("-" * 80)
    
    for activity in activities:
        activity_id = activity.get("Id", "N/A")
        txn_date = activity.get("TxnDate", "N/A")
        
        # Employee
        emp_ref = activity.get("EmployeeRef", {})
        emp_name = emp_ref.get("name", "N/A") if isinstance(emp_ref, dict) else "N/A"
        
        # Ore
        hours = activity.get("Hours", 0)
        minutes = activity.get("Minutes", 0)
        time_str = f"{hours}h {minutes}m"
        
        # Descrizione
        description = activity.get("Description", "")[:30]
        
        print(f"{activity_id:<10} {txn_date:<12} {emp_name:<20} {time_str:<8} {description:<30}")

def find_customer_by_project_name(access_token, project_name):
    """Trova il Customer ID per nome del progetto (cerca nei sub-customer)"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    
    # Prima cerca nei Customer principali
    query = f"SELECT * FROM Customer WHERE DisplayName LIKE '%{project_name}%'"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params={"query": query})
        if response.status_code == 200:
            data = response.json()
            customers = data.get("QueryResponse", {}).get("Customer", [])
            
            if not isinstance(customers, list):
                customers = [customers] if customers else []
            
            for customer in customers:
                display_name = customer.get("DisplayName", "")
                if project_name.lower() in display_name.lower():
                    logging.info(f"Trovato Customer '{display_name}' per progetto '{project_name}' (ID: {customer['Id']})")
                    return customer["Id"]
        
        # Se non trovato nei Customer principali, cerca in tutti i Customer per corrispondenza parziale
        query_all = "SELECT * FROM Customer"
        response = requests.get(url, headers=headers, params={"query": query_all})
        
        if response.status_code == 200:
            data = response.json()
            all_customers = data.get("QueryResponse", {}).get("Customer", [])
            
            if not isinstance(all_customers, list):
                all_customers = [all_customers] if all_customers else []
            
            # Cerca corrispondenza nel nome
            for customer in all_customers:
                display_name = customer.get("DisplayName", "")
                
                # Verifica se il nome del progetto è contenuto nel display name del customer
                if project_name.lower() in display_name.lower():
                    logging.info(f"Trovato Customer '{display_name}' per progetto '{project_name}' (ID: {customer['Id']})")
                    return customer["Id"]
                
                # Verifica anche corrispondenza inversa (nome customer nel nome progetto)
                if display_name.lower() in project_name.lower():
                    logging.info(f"Trovato Customer '{display_name}' per progetto '{project_name}' (ID: {customer['Id']})")
                    return customer["Id"]
        
        logging.warning(f"Nessun Customer trovato per il progetto '{project_name}'")
        return None
        
    except Exception as e:
        logging.error(f"Errore ricerca customer per progetto: {e}")
        return None

def find_customers_by_project_name_fuzzy(access_token, project_name):
    """Trova tutti i Customer che potrebbero corrispondere al nome progetto (ricerca fuzzy)"""
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = "SELECT * FROM Customer"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    matches = []
    
    try:
        response = requests.get(url, headers=headers, params={"query": query})
        if response.status_code == 200:
            data = response.json()
            customers = data.get("QueryResponse", {}).get("Customer", [])
            
            if not isinstance(customers, list):
                customers = [customers] if customers else []
            
            project_words = set(project_name.lower().split())
            
            for customer in customers:
                display_name = customer.get("DisplayName", "")
                customer_words = set(display_name.lower().split())
                
                # Calcola similarità
                common_words = project_words.intersection(customer_words)
                if common_words:
                    similarity = len(common_words) / len(project_words.union(customer_words))
                    if similarity > 0.3:  # Almeno 30% di similarità
                        matches.append({
                            'id': customer["Id"],
                            'name': display_name,
                            'similarity': similarity
                        })
            
            # Ordina per similarità
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            logging.info(f"Trovati {len(matches)} possibili match per progetto '{project_name}'")
            
            return matches
        
        return []
        
    except Exception as e:
        logging.error(f"Errore ricerca fuzzy customer: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Elimina TimeActivity da QuickBooks")
    parser.add_argument("--customer-id", help="ID del customer")
    parser.add_argument("--project-name", help="Nome del progetto (cerca nel nome del customer)")
    parser.add_argument("--employee", help="Nome dell'employee")
    parser.add_argument("--date", help="Data specifica (YYYY-MM-DD)")
    parser.add_argument("--date-from", help="Data inizio (YYYY-MM-DD)")
    parser.add_argument("--date-to", help="Data fine (YYYY-MM-DD)")
    parser.add_argument("--last-days", type=int, help="Elimina ore degli ultimi N giorni")
    parser.add_argument("--preview", action="store_true", help="Solo anteprima, non eliminare")
    parser.add_argument("--force", action="store_true", help="Elimina senza conferma")
    parser.add_argument("--fuzzy-search", action="store_true", help="Mostra tutti i possibili match per nome progetto")
    
    args = parser.parse_args()
    
    # Inizializza connessione
    access_token = init_quickbooks_connection()
    if not access_token:
        sys.exit(1)
    
    # Se richiesta ricerca fuzzy, mostra i possibili match
    if args.fuzzy_search and args.project_name:
        print(f"🔍 Ricerca fuzzy per progetto: '{args.project_name}'")
        matches = find_customers_by_project_name_fuzzy(access_token, args.project_name)
        if matches:
            print(f"\n📋 Possibili match trovati ({len(matches)}):")
            for i, match in enumerate(matches[:10], 1):  # Mostra top 10
                print(f"{i:2d}. {match['name']} (ID: {match['id']}, similarità: {match['similarity']:.2f})")
        else:
            print("❌ Nessun match trovato")
        return
    
    # Costruisci filtri
    filters = {}
    
    if args.customer_id:
        filters['customer_id'] = args.customer_id
    
    if args.project_name:
        filters['project_name'] = args.project_name
    
    if args.employee:
        filters['employee_name'] = args.employee
    
    if args.date:
        filters['date_exact'] = args.date
    
    if args.date_from:
        filters['date_from'] = args.date_from
    
    if args.date_to:
        filters['date_to'] = args.date_to
    
    if args.last_days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.last_days)).strftime("%Y-%m-%d")
        filters['date_from'] = start_date
        filters['date_to'] = end_date
        print(f"Eliminazione ore dal {start_date} al {end_date}")
    
    # Recupera TimeActivity
    print("Ricerca TimeActivity in corso...")
    activities = get_time_activities(access_token, filters)
    
    if not activities:
        print("Nessuna TimeActivity trovata con i filtri specificati.")
        return
    
    # Mostra dettagli
    show_activity_details(activities)
    
    # Se è solo anteprima, esci
    if args.preview:
        print(f"\n🔍 ANTEPRIMA: Trovate {len(activities)} TimeActivity da eliminare")
        return
    
    # Conferma eliminazione
    if not args.force:
        confirm = input(f"\n⚠️  Eliminare {len(activities)} TimeActivity? (s/N): ")
        if confirm.lower() not in ['s', 'si', 'y', 'yes']:
            print("Operazione annullata.")
            return
    
    # Procedi con eliminazione
    print(f"\n🗑️  Eliminazione di {len(activities)} TimeActivity in corso...")
    
    success_count = 0
    error_count = 0
    
    for i, activity in enumerate(activities, 1):
        print(f"Eliminazione {i}/{len(activities)}...", end=' ')
        
        if delete_time_activity(access_token, activity):
            success_count += 1
        else:
            error_count += 1
    
    print(f"\n✅ COMPLETATO:")
    print(f"   Eliminate: {success_count}")
    print(f"   Errori: {error_count}")

if __name__ == "__main__":
    main()
