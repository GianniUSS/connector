import logging
from datetime import datetime
import sys

from rentman_api import list_projects_by_date, get_project_and_customer
from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
from qb_time_activity import inserisci_ore

# Imposta logging su console e file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("integration_log.txt"),
        logging.StreamHandler()
    ]
)

def import_hours_for_period(from_date, to_date, employee_name="GINUDDO", hours_per_project=8, hourly_rate=50):
    """
    Importa ore per tutti i progetti in un periodo specifico.
    
    Args:
        from_date (str): Data inizio formato YYYY-MM-DD
        to_date (str): Data fine formato YYYY-MM-DD  
        employee_name (str): Nome dell'employee
        hours_per_project (int): Ore standard per progetto (default 8)
        hourly_rate (float): Tariffa oraria (default 50)
    """
    logging.info(f"=== IMPORTAZIONE ORE PERIODO: {from_date} - {to_date} ===")
    logging.info(f"Employee: {employee_name}")
    logging.info(f"Ore per progetto: {hours_per_project}")
    logging.info(f"Tariffa oraria: €{hourly_rate}")
    
    try:
        # STEP 1: Recupera progetti nel periodo
        logging.info("STEP 1: Recupero progetti nel periodo specificato")
        projects = list_projects_by_date(from_date, to_date)
        
        if not projects:
            logging.warning("Nessun progetto trovato nel periodo specificato")
            return {"success": True, "message": "Nessun progetto trovato nel periodo", "processed": 0}
        
        logging.info(f"Trovati {len(projects)} progetti nel periodo")
        
        results = []
        successful = 0
        errors = 0
        
        # STEP 2: Processa ogni progetto
        for i, project_summary in enumerate(projects, 1):
            project_id = project_summary.get('id')
            project_name = project_summary.get('name', 'Nome sconosciuto')
            
            logging.info(f"STEP 2.{i}: Elaborazione progetto {project_id} - {project_name}")
            
            try:
                # Recupera dati completi del progetto
                rentman_data = get_project_and_customer(project_id)
                project = rentman_data["project"]
                customer = rentman_data["customer"]
                
                # Mapping dei dati
                customer_data = map_rentman_to_qbo_customer(customer)
                subcustomer_data = map_rentman_to_qbo_subcustomer(project)
                
                # Trova/crea customer e subcustomer (necessari per le time activities)
                qb_customer = trova_o_crea_customer(customer_data["DisplayName"], customer_data)
                if not qb_customer:
                    raise Exception("Customer non trovato/creato")
                
                qb_subcustomer = trova_o_crea_subcustomer(
                    subcustomer_data["DisplayName"], 
                    qb_customer["Id"], 
                    subcustomer_data
                )
                if not qb_subcustomer:
                    raise Exception("Sub-customer non trovato/creato")
                
                # Inserisci ore per questo progetto
                project_number = project.get("number", "")
                activity_date = to_date  # Usa la data finale del periodo
                
                result_time_activity = inserisci_ore(
                    employee_name=employee_name,
                    subcustomer_id=qb_subcustomer["Id"],
                    hours=hours_per_project,
                    hourly_rate=hourly_rate,
                    activity_date=activity_date,
                    description=f"Ore lavorate progetto {project_number} - {project_name}"
                )
                
                logging.info(f"✅ Ore inserite per progetto {project_id}: {result_time_activity}")
                
                results.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "status": "success",
                    "hours": hours_per_project,
                    "rate": hourly_rate,
                    "total": hours_per_project * hourly_rate
                })
                successful += 1
                
            except Exception as e:
                logging.error(f"❌ Errore progetto {project_id}: {e}")
                results.append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "status": "error",
                    "error": str(e)
                })
                errors += 1
        
        # STEP 3: Risultati finali
        total_hours = successful * hours_per_project
        total_amount = total_hours * hourly_rate
        
        logging.info(f"=== IMPORTAZIONE ORE COMPLETATA ===")
        logging.info(f"Progetti elaborati: {len(projects)}")
        logging.info(f"Successi: {successful}")
        logging.info(f"Errori: {errors}")
        logging.info(f"Ore totali inserite: {total_hours}")
        logging.info(f"Importo totale: €{total_amount}")
        
        return {
            "success": True,
            "message": f"Importazione completata: {successful} successi, {errors} errori",
            "processed": len(projects),
            "successful": successful,
            "errors": errors,
            "total_hours": total_hours,
            "total_amount": total_amount,
            "results": results
        }
        
    except Exception as e:
        logging.error(f"ERRORE durante importazione ore: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    # Parametri da riga di comando o default
    if len(sys.argv) >= 3:
        from_date = sys.argv[1]
        to_date = sys.argv[2]
        employee_name = sys.argv[3] if len(sys.argv) > 3 else "GINUDDO"
    else:
        # Valori di test
        from_date = "2025-05-24"
        to_date = "2025-05-27"
        employee_name = "GINUDDO"
    
    result = import_hours_for_period(from_date, to_date, employee_name)
    print(f"Risultato importazione: {result}")