import logging
from datetime import datetime

from rentman_api import get_project_and_customer
from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
# Importiamo direttamente la funzione
from create_or_update_invoice_for_project import create_or_update_invoice_for_project

# Imposta logging su console e file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("integration_log.txt"),
        logging.StreamHandler()
    ]
)

def main_invoice_only(project_id):
    """
    Elabora solo la parte fatturazione per un progetto:
    - Crea/aggiorna Customer
    - Crea/aggiorna Sub-customer (progetto)  
    - Crea/aggiorna Invoice
    
    NON gestisce le ore lavorate.
    """
    logging.info(f"=== ELABORAZIONE FATTURA - PROJECT ID: {project_id} ===")
    
    try:
        # STEP 1: Recupero dati progetto e cliente da Rentman
        logging.info(f"STEP 1: Recupero dati progetto e cliente da Rentman (project_id={project_id})")
        rentman_data = get_project_and_customer(project_id)
        project = rentman_data["project"]
        customer = rentman_data["customer"]

        logging.info(f"Project Rentman: {project.get('name')}")
        logging.info(f"Customer Rentman: {customer.get('name')}")

        # Mapping dei dati
        customer_data = map_rentman_to_qbo_customer(customer)
        subcustomer_data = map_rentman_to_qbo_subcustomer(project)

        # STEP 2: Trova o crea CUSTOMER su QuickBooks
        logging.info("STEP 2: Trova o crea CUSTOMER su QuickBooks")
        qb_customer = trova_o_crea_customer(customer_data["DisplayName"], customer_data)
        if not qb_customer:
            logging.error("ERRORE: customer non trovato/creato.")
            return {"success": False, "error": "Customer non trovato/creato"}

        # STEP 3: Trova o crea SUB-CUSTOMER (progetto) su QuickBooks
        logging.info("STEP 3: Trova o crea SUB-CUSTOMER (progetto) su QuickBooks")
        qb_subcustomer = trova_o_crea_subcustomer(subcustomer_data["DisplayName"], qb_customer["Id"], subcustomer_data)
        if not qb_subcustomer:
            logging.error("ERRORE: sub-customer non trovato/creato.")
            return {"success": False, "error": "Sub-customer non trovato/creato"}

        logging.info(f"Customer QBO: {qb_customer['DisplayName']} (ID: {qb_customer['Id']})")
        logging.info(f"Sub-customer QBO: {qb_subcustomer['DisplayName']} (ID: {qb_subcustomer['Id']})")

        # Dati per la fattura
        project_number = project.get("number", "")
        amount = float(project.get("project_total_price", 0))
        descrizione = project.get("name", "Fattura progetto Rentman")
        invoice_date = datetime.today().strftime("%Y-%m-%d")

        # STEP 4: CERCA o CREA/AGGIORNA INVOICE su QuickBooks
        logging.info("STEP 4: CERCA o CREA/AGGIORNA INVOICE su QuickBooks")
        result_invoice = create_or_update_invoice_for_project(
            subcustomer_id=qb_subcustomer["Id"],
            project_id=project_id,
            project_number=project_number,
            amount=amount,
            descrizione=descrizione,
            invoice_date=invoice_date,
        )

        logging.info(f"Risultato operazione Invoice: {result_invoice}")
        logging.info(f"=== COMPLETATA ELABORAZIONE FATTURA - PROJECT ID: {project_id} ===")
        
        # Verifica se siamo in modalità simulazione
        is_simulated = result_invoice.get("simulated", False)
        if is_simulated:
            logging.warning("Operazione in modalità simulazione - token QuickBooks non valido")
        
        return {
            "success": True, 
            "project_id": project_id,
            "project_name": project.get('name'),
            "invoice_result": result_invoice,
            "customer": qb_customer['DisplayName'],
            "subcustomer": qb_subcustomer['DisplayName'],
            "simulated": is_simulated
        }
        
    except Exception as e:
        logging.error(f"ERRORE durante elaborazione progetto {project_id}: {e}")
        return {"success": False, "error": str(e), "project_id": project_id}

if __name__ == "__main__":
    # Test standalone
    project_id = "3336"
    result = main_invoice_only(project_id)
    print(f"Risultato: {result}")