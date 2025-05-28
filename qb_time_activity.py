
import requests
import config
import logging
from token_manager import TokenManager
    
# Crea una sola istanza del TokenManager per tutto il file
token_manager = TokenManager()
access_token = token_manager.get_access_token()    

def find_employee_by_name(name, access_token):
    url = f"{config.API_BASE_URL}{config.REALM_ID}/query"
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

    url = f"{config.API_BASE_URL}{config.REALM_ID}/employee"
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

    url = f"{config.API_BASE_URL}{config.REALM_ID}/query"
    query = (
        f"SELECT * FROM TimeActivity WHERE CustomerRef = '{subcustomer_id}' "
        f"AND TxnDate = '{activity_date}'"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    logging.info(f"[QUERY] Cerco TimeActivity con CustomerRef='{subcustomer_id}', TxnDate='{activity_date}' (filtro EmployeeRef in Python)")
    response = requests.get(url, headers=headers, params={"query": query})
    logging.info(f"[RESPONSE] Status: {response.status_code}")

    if response.status_code == 200:
        activities = response.json().get("QueryResponse", {}).get("TimeActivity", [])
        for activity in activities:
            emp_ref = activity.get("EmployeeRef", {}).get("value")
            act_id = activity.get("Id")
            if emp_ref == str(employee_id):
                logging.info(f"[FOUND] Trovata TimeActivity ID: {act_id} per EmployeeRef='{employee_id}'")
                return activity
        logging.info("[NOT FOUND] Nessuna TimeActivity corrispondente trovata per l'employee_id.")
    else:
        err_msg = response.json().get("Fault", {}).get("Error", [{}])[0].get("Message", "Errore sconosciuto")
        logging.error(f"[ERROR] Errore nella query TimeActivity: {response.status_code} - {err_msg}")

    return None

def inserisci_ore(employee_name, subcustomer_id, hours, hourly_rate, activity_date, description):
    token_manager = TokenManager()
    access_token = token_manager.get_access_token()

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
        "Minutes": 0,
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
