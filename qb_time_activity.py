import requests
import config
import logging
from token_manager import token_manager
import openpyxl
import os
from datetime import datetime
    
# Rimuovi la creazione locale di TokenManager
# token_manager = TokenManager()
access_token = token_manager.get_access_token()    

def find_employee_by_name(name, access_token):
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM Employee WHERE DisplayName = '{name}'"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers, params={"query": query})
    if response.status_code == 200:
        data = response.json()
        employees = data.get("QueryResponse", {}).get("Employee", [])
        if employees:
            return employees[0]["Id"]
    return None

def create_employee(name, access_token):
    import logging

    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/employee"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Separa il nome per ottenere GivenName e FamilyName
    name_parts = name.strip().split()
    given_name = name_parts[0]
    family_name = name_parts[-1] if len(name_parts) > 1 else name_parts[0]

    payload = {
        "DisplayName": name,
        "GivenName": given_name,
        "FamilyName": family_name
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return response.json()["Employee"]["Id"]
    else:
        error_info = response.json().get("Fault", {}).get("Error", [{}])[0]
        logging.error(f"Errore nella creazione del dipendente: {error_info.get('Message')} - {error_info.get('Detail')}")
        return None


def find_existing_time_activity(subcustomer_id, employee_id, activity_date, access_token):
    import logging
    import requests
    
    logging.info(f"[find_existing_time_activity] activity_date ricevuta: '{activity_date}' (tipo: {type(activity_date)})")
    
    if not activity_date:
        logging.error("[find_existing_time_activity] activity_date mancante o vuoto: query non eseguita.")
        return None
    
    # Assicurati che la data sia in formato YYYY-MM-DD
    if isinstance(activity_date, str) and len(activity_date) > 10:
        activity_date = activity_date[:10]
    
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Strategia 1: Prova prima con una query semplice per data
    query_simple = f"SELECT * FROM TimeActivity WHERE TxnDate = '{activity_date}'"
    
    logging.info(f"[find_existing_time_activity] Eseguendo query: {query_simple}")
    
    response = requests.get(url, headers=headers, params={"query": query_simple})
    
    if response.status_code == 200:
        data = response.json()
        activities = data.get("QueryResponse", {}).get("TimeActivity", [])
        
        if activities:
            # Se non è una lista, convertila
            if not isinstance(activities, list):
                activities = [activities]
            
            # Filtra manualmente per Employee e Customer
            for activity in activities:
                # Controlla EmployeeRef
                employee_ref = activity.get("EmployeeRef", {})
                emp_id = employee_ref.get("value") if isinstance(employee_ref, dict) else str(employee_ref)
                
                # Controlla CustomerRef
                customer_ref = activity.get("CustomerRef", {})
                cust_id = customer_ref.get("value") if isinstance(customer_ref, dict) else str(customer_ref)
                
                logging.info(f"TimeActivity ID: {activity.get('Id')}, Employee: {emp_id}, Customer: {cust_id}")
                
                if str(emp_id) == str(employee_id) and str(cust_id) == str(subcustomer_id):
                    logging.info(f"Trovata TimeActivity ID: {activity.get('Id')} per Employee='{employee_id}', Customer='{subcustomer_id}', Data='{activity_date}'")
                    return activity
        
        logging.info(f"Nessuna TimeActivity trovata per Employee='{employee_id}', Customer='{subcustomer_id}', Data='{activity_date}'")
    
    else:
        try:
            error_data = response.json()
            err_msg = error_data.get("Fault", {}).get("Error", [{}])[0].get("Message", "Errore sconosciuto")
            logging.error(f"Errore nella query TimeActivity: {response.status_code} - {err_msg}")
            logging.error(f"Query utilizzata: {query_simple}")
        except:
            logging.error(f"Errore nella query TimeActivity: {response.status_code} - {response.text}")
    
    return None

def inserisci_ore(employee_name, subcustomer_id, hours, minutes, hourly_rate, activity_date, description):
    from datetime import datetime
    # Rimuovi la creazione locale di TokenManager
    # token_manager = TokenManager()
    access_token = token_manager.get_access_token()

    # Normalizza la data nel formato YYYY-MM-DD
    try:
        if activity_date:
            activity_date = datetime.strptime(str(activity_date)[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception as e:
        logging.warning(f"Data attività non valida: {activity_date}, errore: {e}. Uso la data odierna.")
        activity_date = datetime.now().strftime("%Y-%m-%d")

    logging.info(f"Verifico la presenza dell'employee '{employee_name}' in QuickBooks...")
    employee_id = find_employee_by_name(employee_name, access_token)
    if not employee_id:
        logging.info(f"Employee '{employee_name}' non trovato. Creo un nuovo dipendente...")
        employee_id = create_employee(employee_name, access_token)
        if not employee_id:
            raise ValueError("Impossibile creare dipendente.")

    logging.info(f"Employee '{employee_name}' pronto con ID {employee_id}. Procedo con inserimento ore...")

    existing = find_existing_time_activity(subcustomer_id, employee_id, activity_date, access_token)

    payload = {
        "TxnDate": activity_date,
        "NameOf": "Employee",
        "EmployeeRef": {"value": employee_id, "name": employee_name},
        "CustomerRef": {"value": subcustomer_id},
        "ItemRef": {"value": "2", "name": "Hours"},
        "BillableStatus": "NotBillable",
        "Taxable": False,
        "HourlyRate": hourly_rate,
        "Hours": hours,
        "Minutes": minutes,
        "Description": description
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    if existing:
        logging.info("Ore già inserite per questa data. Aggiorno la TimeActivity...")
        payload["Id"] = existing["Id"]
        payload["SyncToken"] = existing["SyncToken"]
        payload["sparse"] = True
        url = f"{config.API_BASE_URL}{config.REALM_ID}/timeactivity?operation=update"
        response = requests.post(url, headers=headers, json=payload)
    else:
        logging.info("Nessuna TimeActivity trovata. Creo una nuova registrazione...")
        url = f"{config.API_BASE_URL}{config.REALM_ID}/timeactivity"
        response = requests.post(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        return response.json()
    else:
        logging.error(f"Errore durante inserimento ore: {response.status_code}, {response.text}")
        return None


def import_ore_da_excel(filepath, data_attivita, hourly_rate=50, descrizione_default="Import ore da Excel"):
    """
    Importa ore lavorate da un file Excel con colonne:
    A: Project ID, B: Nominativo dipendente, C: Ore lavorate (HH:MM)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File non trovato: {filepath}")
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    risultati = []
    for i, row in enumerate(ws.iter_rows(min_row=2), start=2):  # Salta header
        project_id = row[0].value
        employee_name = row[1].value
        ore_str = row[2].value
        if not (project_id and employee_name and ore_str):
            risultati.append({"row": i, "project_id": project_id, "employee_name": employee_name, "ore": ore_str, "esito": "Dati mancanti"})
            continue
        # Conversione ore HH:MM → ore e minuti separati
        try:
            if isinstance(ore_str, (int, float)):
                hours = int(ore_str)
                minutes = int(round((float(ore_str) - hours) * 60))
            else:
                ore_parts = str(ore_str).strip().split(":")
                hours = int(ore_parts[0])
                minutes = int(ore_parts[1]) if len(ore_parts) > 1 else 0
        except Exception as e:
            risultati.append({"row": i, "project_id": project_id, "employee_name": employee_name, "ore": ore_str, "esito": f"Errore conversione ore: {e}"})
            continue
        # NON chiamare inserisci_ore qui! Solo verifica dati, nessuna chiamata a QB
        risultati.append({
            "row": i,
            "project_id": project_id,
            "employee_name": employee_name,
            "hours": hours,
            "minutes": minutes,
            "esito": "OK"
        })
    return risultati
