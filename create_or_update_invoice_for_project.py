# filepath: e:\AppConnettor\create_or_update_invoice_for_project.py
"""
Modulo per la creazione o l'aggiornamento di fatture in QuickBooks.
"""

import requests
import config
import logging
from token_manager import token_manager
import json

# Esportiamo esplicitamente la funzione principale
__all__ = ['create_or_update_invoice_for_project']

def get_access_token():
    token_manager.load_refresh_token()
    return token_manager.get_access_token()

def find_invoice_by_number(invoice_number):
    """Cerca una fattura in QuickBooks in base al numero documento"""
    access_token = get_access_token()
    
    # Verifica se stiamo usando un token fittizio (per token scaduto)
    if access_token == "invalid_token_handled_gracefully":
        logging.warning(f"Token non valido, impossibile cercare fattura {invoice_number} in QuickBooks")
        return None
    
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM Invoice WHERE DocNumber = '{invoice_number}'"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    params = {"query": query}
    logging.info(f"Ricerca invoice con DocNumber={invoice_number} su QBO...")
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        logging.error(f"Errore ricerca Invoice: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    if 'Invoice' in data.get('QueryResponse', {}):
        logging.info("Invoice trovata!")
        return data['QueryResponse']['Invoice'][0]
    logging.info("Invoice non trovata, sarà creata.")
    return None

def create_or_update_invoice_for_project(
    subcustomer_id,
    project_id,
    project_number,
    amount,
    descrizione,
    invoice_date,
    class_id="540302",
    tax_id="8"
):
    """
    Crea o aggiorna una fattura in QuickBooks per un progetto specifico.
    
    Args:
        subcustomer_id (str): ID del sub-cliente in QuickBooks
        project_id (str): ID del progetto in Rentman
        project_number (str): Numero del progetto
        amount (float): Importo della fattura
        descrizione (str): Descrizione della fattura
        invoice_date (str): Data della fattura in formato YYYY-MM-DD
        class_id (str, optional): ID della classe QuickBooks. Default "540302".
        tax_id (str, optional): ID dell'aliquota fiscale. Default "8".
        
    Returns:
        dict: Risultato dell'operazione con informazioni sulla fattura
    """
    access_token = get_access_token()
    
    # Verifica se stiamo usando un token fittizio (per token scaduto)
    if access_token == "invalid_token_handled_gracefully":
        logging.warning("Token non valido, impossibile creare/aggiornare fattura in QuickBooks")
        return {
            "success": True,
            "invoice_id": "simulato_" + str(project_id),
            "doc_number": f"{project_number}_{project_id}",
            "simulated": True,
            "message": "Modalità simulazione: token QuickBooks non valido"
        }
    
    invoice_number = f"{project_number}_{project_id}"
    invoice = find_invoice_by_number(invoice_number)

    # Se siamo in modalità simulazione e abbiamo trovato una fattura, restituisci una risposta simulata di aggiornamento
    if access_token == "invalid_token_handled_gracefully" and invoice:
        logging.warning(f"Token non valido, impossibile aggiornare fattura {invoice_number} in QuickBooks")
        return {
            "success": True,
            "invoice_id": invoice.get("Id", "simulato_" + str(project_id)),
            "doc_number": invoice_number,
            "simulated": True,
            "message": "Modalità simulazione: aggiornamento fattura simulato (token QuickBooks non valido)"
        }

    invoice_payload = {
        "CustomerRef": {"value": str(subcustomer_id)},
        "DocNumber": invoice_number,
        "TxnDate": invoice_date,
        "Line": [
            {
                "DetailType": "SalesItemLineDetail",
                "Amount": amount,
                "Description": descrizione,
                "SalesItemLineDetail": {
                    "ItemRef": {"value": "1"},
                    "ClassRef": {"value": str(class_id)},
                    "TaxCodeRef": {"value": str(tax_id)},
                    "Qty": 1,
                    "UnitPrice": amount
                }
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Doppio controllo per assicurarci di non essere in modalità simulazione
    if access_token == "invalid_token_handled_gracefully":
        logging.warning("Token non valido, impossibile creare/aggiornare fattura in QuickBooks")
        return {
            "success": True,
            "invoice_id": "simulato_" + str(project_id),
            "doc_number": invoice_number,
            "simulated": True,
            "message": "Modalità simulazione: token QuickBooks non valido"
        }

    if invoice:
        invoice_payload["Id"] = invoice["Id"]
        invoice_payload["SyncToken"] = invoice["SyncToken"]
        invoice_payload["sparse"] = True
        url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/invoice?operation=update"
        logging.info(f"Aggiorno la invoice esistente (DocNumber={invoice_number})")
        resp = requests.post(url, headers=headers, json=invoice_payload)
        logging.info(f"Invoice aggiornata (DocNumber={invoice_number}) - Status: {resp.status_code}")
    else:
        url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/invoice"
        logging.info(f"Creo una nuova invoice per il progetto {project_number} (DocNumber={invoice_number})")
        resp = requests.post(url, headers=headers, json=invoice_payload)
        logging.info(f"Invoice creata (DocNumber={invoice_number}) - Status: {resp.status_code}")
    
    try:
        if resp.status_code >= 400:
            logging.error(f"Errore API QuickBooks: {resp.status_code} {resp.text}")
            return {
                "success": False,
                "error": f"QuickBooks API error: {resp.status_code}",
                "details": resp.text
            }
        
        # Estrai l'ID fattura dalla risposta
        response_json = resp.json()
        invoice_id = response_json.get("Invoice", {}).get("Id", "sconosciuto")
        logging.info(f"Invoice ID: {invoice_id}")
        
        return {
            "success": True,
            "invoice_id": invoice_id,
            "doc_number": invoice_number
        }
    except Exception as e:
        error_msg = f"Errore parsing risposta Invoice: {e}"
        logging.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "response_code": getattr(resp, 'status_code', 'N/A'),
            "response_text": getattr(resp, 'text', 'N/A')
        }


# Se eseguito direttamente, mostra informazioni di debug
if __name__ == "__main__":
    print("Questo è il modulo per la creazione o aggiornamento di fatture in QuickBooks.")
    print("Importa la funzione create_or_update_invoice_for_project per utilizzarla.")
