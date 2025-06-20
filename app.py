from flask import Flask, request, jsonify, send_from_directory, render_template
from rentman_api import get_project_and_customer
from qb_customer import set_qb_import_status, get_qb_import_status
from create_or_update_invoice_for_project import create_or_update_invoice_for_project
from qb_time_activity import import_ore_da_excel, inserisci_ore
# 🚀 NUOVO MODULO UNIFICATO per progetti - FIXED CLEAN VERSION
from rentman_projects_fixed_clean import (
    list_projects_by_date_unified,
    list_projects_by_date_paginated_full_unified,
    list_projects_by_date_paginated_unified,  # 🚀 AGGIUNTO per endpoint ottimizzato
    filter_projects_by_status,
    list_projects_by_number_full_unified  # <--- aggiunto import
)
import rentman_project_utils
import time
import subprocess
import os
import tempfile
import csv
import io
import re
from quickbooks_taxcode_cache import get_taxcode_id
import logging
from token_manager import token_manager
import requests
import config

# 🚀 PERFORMANCE OPTIMIZATIONS
from performance_optimizations import (
    optimize_project_list_loading,
    optimize_selected_projects_processing,
    performance_monitor
)

# Configura logging - TEMPORANEAMENTE DEBUG per vedere i log project_type_name
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
 

# Import diretti delle funzioni invece di subprocess
try:
    from main_invoice_only import main_invoice_only
    INVOICE_IMPORT_SUCCESS = True
    print("✅ main_invoice_only importato con successo")
except ImportError as e:
    print(f"⚠️ Impossibile importare main_invoice_only: {e}")
    print("📝 Verrà usato subprocess come fallback")
    INVOICE_IMPORT_SUCCESS = False

try:
    # Proviamo a importare la funzione create_or_update_invoice_for_project
    from create_or_update_invoice_for_project import create_or_update_invoice_for_project
    CREATE_INVOICE_IMPORT_SUCCESS = True
    print("✅ create_or_update_invoice_for_project importato con successo")
except ImportError as e:
    print(f"⚠️ Impossibile importare create_or_update_invoice_for_project: {e}")
    CREATE_INVOICE_IMPORT_SUCCESS = False

try:
    from import_hours_by_date import import_hours_for_period
    HOURS_IMPORT_SUCCESS = True
    print("✅ import_hours_by_date importato con successo")
except ImportError as e:
    print(f"⚠️ Impossibile importare import_hours_by_date: {e}")
    print("📝 Verrà usato subprocess come fallback")
    HOURS_IMPORT_SUCCESS = False

app = Flask(__name__)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve file statici dalla cartella static"""
    return send_from_directory('static', path)

@app.route('/api/token-status')
def token_status():
    """Restituisce lo stato del token QuickBooks"""
    
    try:
        token_manager.load_refresh_token()
        access_token = token_manager.get_access_token()
        
        is_valid = access_token != "invalid_token_handled_gracefully"
        
        return jsonify({
            'valid': is_valid,
            'mode': 'normale' if is_valid else 'simulazione',
            'message': 'Token QuickBooks valido' if is_valid else 'Token QuickBooks non valido - Modalità simulazione attiva'
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'mode': 'errore',
            'message': f'Errore verifica token: {str(e)}'
        })

@app.route('/avvia-importazione', methods=['POST'])
def avvia_importazione_ore():
    """Importa ore per tutti i progetti nel periodo specificato"""
    data = request.json
    from_date = data.get('fromDate')
    to_date = data.get('toDate')
    employee_name = data.get('employeeName', 'GINUDDO')
    
    print(f"🕐 AVVIO IMPORTAZIONE ORE")
    print(f"   📅 Periodo: {from_date} - {to_date}")
    print(f"   👤 Employee: {employee_name}")
    
    try:
        if HOURS_IMPORT_SUCCESS:
            # Usa import diretto
            print("🔗 Usando import diretto per importazione ore")
            result = import_hours_for_period(from_date, to_date, employee_name)
            
            if result.get('success'):
                print("✅ Importazione ore completata con successo")
                return jsonify({
                    'success': True,
                    'message': result.get('message', 'Importazione ore completata'),
                    'output': str(result),
                    'details': result
                })
            else:
                print(f"❌ Errore durante importazione ore: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'message': 'Errore durante importazione ore',
                    'error': result.get('error', 'Errore sconosciuto'),
                    'details': result
                })
        else:
            # Fallback subprocess
            print("🔄 Usando subprocess come fallback")
            result = subprocess.run(
                ['python', 'import_hours_by_date.py', from_date, to_date, employee_name],
                capture_output=True, 
                text=True,
                timeout=600  # 10 minuti timeout
            )
            
            if result.returncode == 0:
                print("✅ Importazione ore completata con successo")
                return jsonify({
                    'success': True,
                    'message': 'Importazione ore completata con successo',
                    'output': result.stdout
                })
            else:
                print(f"❌ Errore durante importazione ore: {result.stderr}")
                return jsonify({
                    'success': False,
                    'message': 'Errore durante importazione ore',
                    'output': result.stdout,
                    'error': result.stderr
                })
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout importazione ore")
        return jsonify({
            'success': False,
            'message': 'Timeout durante importazione ore (>10 minuti)',
            'error': 'Operazione troppo lunga'
        })
    except Exception as e:
        print(f"💥 Errore importazione ore: {e}")
        return jsonify({
            'success': False,
            'message': 'Errore durante importazione ore',
            'error': str(e)
        })

@app.route('/api/lista-progetti', methods=['GET', 'POST'])
def lista_progetti():
    """
    Endpoint che restituisce i progetti per la grid web, con logica identica allo script standalone:
    - Recupera tutti i progetti dalla collection /projects (paginazione)
    - Filtra in locale per data
    - Recupera dettagli progetto (cliente, responsabile, tipo, valore, email)
    - Filtra per stato
    - Restituisce i dati per la grid
    """
    if request.method == 'GET':
        from_date = request.args.get('date') or request.args.get('fromDate')
    else:
        data = request.get_json(force=True, silent=True) or {}
        from_date = data.get('fromDate')
    stati_interesse = ["In location", "Rientrato", "Confermato", "Pronto"]
    headers = {
        'Authorization': f'Bearer {os.environ.get("REN_API_TOKEN", "")}',
        'Accept': 'application/json'
    }
    base_url = getattr(config, 'REN_BASE_URL', 'https://api.rentman.net')
    # 1. Scarica tutti i progetti grezzi con paginazione
    url = f"{base_url}/projects"
    params = {
        'sort': '+id',
        'id[gt]': 2900,
        'fields': 'id,name,number,planperiod_start,planperiod_end',
        'limit': 150,
        'offset': 0
    }
    all_projects = []
    while True:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if not resp.ok:
            break
        page_projects = resp.json().get('data', [])
        all_projects.extend(page_projects)
        if len(page_projects) < params['limit']:
            break
        params['offset'] += params['limit']
    # 2. Filtro locale per data
    filtered_projects = rentman_project_utils.filter_projects_by_date(all_projects, from_date)
    # 3. Recupera dettagli progetto
    detailed_projects = []
    for p in filtered_projects:
        project_id = p.get('id')
        project_url = f"{base_url}/projects/{project_id}"
        resp = requests.get(project_url, headers=headers, timeout=10)
        if not resp.ok:
            continue
        data = resp.json().get('data', {})
        # Cliente
        customer_name = ""
        customer_path = data.get('customer')
        if customer_path:
            customer_id = rentman_project_utils.extract_id_from_path(customer_path)
            if customer_id:
                customer_url = f"{base_url}/contacts/{customer_id}"
                cust_resp = requests.get(customer_url, headers=headers, timeout=10)
                if cust_resp.ok:
                    cust_data = cust_resp.json().get('data', {})
                    customer_name = cust_data.get('displayname') or cust_data.get('name', '')
        # Responsabile
        manager_name = None
        manager_email = None
        account_manager_path = data.get('account_manager')
        if account_manager_path:
            manager_id = rentman_project_utils.extract_id_from_path(account_manager_path)
            if manager_id:
                crew_url = f"{base_url}/crew/{manager_id}"
                crew_resp = requests.get(crew_url, headers=headers, timeout=10)
                if crew_resp.ok:
                    crew_data = crew_resp.json().get('data', {})
                    manager_name = crew_data.get('name') or crew_data.get('displayname')
                    manager_email = crew_data.get('email') or crew_data.get('email_1')
        # Tipo progetto
        project_type_name = ""
        project_type_path = data.get('project_type')
        if project_type_path:
            project_type_id = rentman_project_utils.extract_id_from_path(project_type_path)
            if project_type_id:
                type_url = f"{base_url}/projecttypes/{project_type_id}"
                type_resp = requests.get(type_url, headers=headers, timeout=10)
                if type_resp.ok:
                    type_data = type_resp.json().get('data', {})
                    project_type_name = type_data.get('name', '')
        # Valore progetto
        valore = data.get('project_total_price')
        try:
            valore = round(float(valore), 2) if valore is not None else None
        except Exception:
            valore = None
        detailed_projects.append({
            'id': project_id,
            'name': p.get('name', ''),
            'number': p.get('number', ''),
            'period_from': p.get('planperiod_start', '')[:10] if p.get('planperiod_start') else '',
            'period_to': p.get('planperiod_end', '')[:10] if p.get('planperiod_end') else '',
            'cliente': customer_name,
            'manager_name': manager_name,
            'manager_email': manager_email,
            'project_type_name': project_type_name,
            'value': valore
        })
    # 4. Filtro per stato
    progetti_stato = rentman_project_utils.filter_projects_by_status(detailed_projects, headers, stati_interesse, base_url)
    # 5. Output per grid
    output = []
    for p, status_name in progetti_stato:
        output.append({
            'id': p.get('id'),
            'number': p.get('number'),
            'name': p.get('name'),
            'status': status_name,
            'period_from': p.get('period_from'),
            'period_to': p.get('period_to'),
            'cliente': p.get('cliente'),
            'manager_name': p.get('manager_name'),
            'manager_email': p.get('manager_email'),
            'project_type_name': p.get('project_type_name'),
            'value': p.get('value')
        })
    return jsonify({'projects': output})

@app.route('/elabora-selezionati', methods=['POST'])
def elabora_selezionati():
    """Elabora fatturazione per progetti selezionati (SENZA ore) - OTTIMIZZATO"""
    data = request.json
    selected_projects = data.get('selectedProjects', [])
    
    if not selected_projects:
        return jsonify({'error': 'Nessun progetto selezionato'}), 400
    
    print(f"💰 ELABORAZIONE FATTURE per {len(selected_projects)} progetti - PROCESSING PARALLELO")
    
    def elabora_fattura_progetto(project_id, project_name):
        """Elabora solo la fatturazione per un singolo progetto"""
        try:
            print(f"💰 Elaborazione fattura progetto {project_id} ({project_name})...")
            
            if INVOICE_IMPORT_SUCCESS:
                # Usa import diretto
                print(f"🔗 Usando import diretto per progetto {project_id}")
                result = main_invoice_only(project_id)
                
                if result.get('success'):
                    # Controlla se l'operazione è stata simulata (token non valido)
                    is_simulated = result.get('simulated', False)
                    status = 'success_simulated' if is_simulated else 'success'
                    set_qb_import_status(project_id, status, result.get('message') or None)
                    
                    if is_simulated:
                        return {
                            'project_id': project_id,
                            'project_name': project_name,
                            'status': status,
                            'output': str(result),
                            'error': None,
                            'details': result,
                            'message': "Operazione simulata: token QuickBooks non valido"
                        }
                    else:
                        return {
                            'project_id': project_id,
                            'project_name': project_name,
                            'status': status,
                            'output': str(result),
                            'error': None,
                            'details': result
                        }
                else:
                    set_qb_import_status(project_id, 'error', result.get('error', 'Errore sconosciuto'))
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'error',
                        'output': str(result),
                        'error': result.get('error', 'Errore sconosciuto'),
                        'details': result
                    }
            else:
                # Fallback subprocess
                print(f"🔄 Usando subprocess per progetto {project_id}")
                result = subprocess.run(
                    ['python', 'main_invoice_only.py', str(project_id)],
                    capture_output=True, 
                    text=True,
                    timeout=120  # 🚀 OTTIMIZZATO: 2 minuti invece di 5
                )
                if result.returncode == 0:
                    set_qb_import_status(project_id, 'success', None)
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'success',
                        'output': result.stdout,
                        'error': None
                    }
                else:
                    set_qb_import_status(project_id, 'error', result.stderr)
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'error',
                        'output': result.stdout,
                        'error': result.stderr
                    }
        except subprocess.TimeoutExpired:
            set_qb_import_status(project_id, 'timeout', 'Timeout dopo 2 minuti')
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': 'timeout',
                'output': '',
                'error': 'Timeout dopo 2 minuti'
            }
        except Exception as e:
            set_qb_import_status(project_id, 'error', str(e))
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': 'error',
                'output': '',
                'error': str(e)
            }    
    # 🚀 OTTIMIZZAZIONE: Elaborazione parallela invece di sequenziale
    try:
        results = optimize_selected_projects_processing(
            selected_projects, 
            elabora_fattura_progetto
        )
    except Exception as e:
        print(f"[ERRORE] Ottimizzazione fallita, fallback a elaborazione sequenziale: {e}")
        # Fallback a elaborazione sequenziale se l'ottimizzazione fallisce
        results = []
        for project in selected_projects:
            project_id = project.get('id')
            project_name = project.get('name', 'Nome sconosciuto')
            
            result = elabora_fattura_progetto(project_id, project_name)
            results.append(result)
            time.sleep(0.5)  # Pausa ridotta per fallback
    
    # Statistiche finali
    success_count = len([r for r in results if r['status'] == 'success'])
    simulated_count = len([r for r in results if r['status'] == 'success_simulated'])
    error_count = len([r for r in results if r['status'] == 'error'])
    timeout_count = len([r for r in results if r['status'] == 'timeout'])
    
    print(f"💰 ELABORAZIONE FATTURE COMPLETATA (PARALLELO):")
    print(f"   ✅ Successi: {success_count}")
    if simulated_count > 0:
        print(f"   🔄 Simulati: {simulated_count} (token QuickBooks non valido)")
    print(f"   ❌ Errori: {error_count}")
    print(f"   ⏰ Timeout: {timeout_count}")
    
    message
    if simulated_count > 0:
        message += f', {simulated_count} simulati (token scaduto)'
    message += f', {error_count} errori, {timeout_count} timeout'
    
    return jsonify({
        'message': message,
        'success': True,
        'results': results,
        'summary': {
            'total': len(selected_projects),
            'success': success_count,
            'simulated': simulated_count,
            'errors': error_count,
            'timeouts': timeout_count
        }
    })

@app.route('/dettaglio-progetto/<int:project_id>', methods=['GET'])
def dettaglio_progetto(project_id):
    try:
        from rentman_api import get_project_and_customer
        data = get_project_and_customer(project_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/importa-ore-excel', methods=['POST'])
def importa_ore_excel():
    """Endpoint per importare ore lavorate da file Excel e inserirle in QuickBooks"""
    if 'excelFile' not in request.files:
        return jsonify({'success': False, 'error': 'File Excel mancante'}), 400
    file = request.files['excelFile']
    data_attivivita = request.form.get('data_attivivita')
    if not data_attivivita:
        return jsonify({'success': False, 'error': 'Data attività mancante'}), 400
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            file.save(tmp.name)
            tmp_filepath = tmp.name
        report = import_ore_da_excel(tmp_filepath, data_attivivita)
        # Rimuovi file temporaneo
        try:
            import os
            os.remove(tmp_filepath)
        except Exception:
            pass
        success_count = sum(1 for r in report if r.get('esito') == 'OK')
        error_count = len(report) - success_count
        return jsonify({
            'success': True,
            'message': f'Importazione completata: {success_count} OK, {error_count} errori',
            'report': report
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/trasferisci-ore-qb', methods=['POST'])
def trasferisci_ore_qb():
    """Endpoint per trasferire le righe OK su QuickBooks, mostrando anche il nome sub-customer"""
    data = request.get_json()
    rows = data.get('rows', [])
    if not rows:
        return jsonify({'success': False, 'error': 'Nessuna riga da trasferire'}), 400
    risultati = []
    for r in rows:
        try:
            # Recupera nome sub-customer da Rentman e dati progetto/cliente
            project_id = r.get('project_id')
            subcustomer_name = None
            qb_customer = None
            qb_subcustomer = None
            try:
                # Ottieni i dati completi da Rentman
                project_data = get_project_and_customer(project_id)
                project = project_data['project']
                customer = project_data['customer']
                subcustomer_name = project.get('name')
                # Mapping dati
                from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
                customer_data = map_rentman_to_qbo_customer(customer)
                subcustomer_data = map_rentman_to_qbo_subcustomer(project)
                # Trova/crea customer e subcustomer in QB
                from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
                qb_customer = trova_o_crea_customer(customer_data["DisplayName"], customer_data)
                if not qb_customer or not qb_customer.get("Id"):
                    raise Exception("Customer non trovato/creato")
                qb_subcustomer = trova_o_crea_subcustomer(subcustomer_data["DisplayName"], qb_customer["Id"], subcustomer_data)
                if not qb_subcustomer or not qb_subcustomer.get("Id"):
                    raise Exception("Sub-customer non trovato/creato")
                # Estrai la data di fine progetto (planperiod_end) da Rentman
                activity_date = project.get("planperiod_end")
                if activity_date:
                    activity_date = str(activity_date)[:10]
                else:
                    risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'Errore: data fine progetto mancante'})
                    continue
            except Exception as e:
                subcustomer_name = subcustomer_name or None
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': f'Errore dati progetto/cliente: {e}'})
                continue
            # Effettua la chiamata a QB usando l'ID corretto del sub-customer e la data estratta
            res = inserisci_ore(
                employee_name=r.get('employee_name'),
                subcustomer_id=qb_subcustomer["Id"],
                hours=int(r.get('hours', 0)),
                minutes=int(r.get('minutes', 0)),
                hourly_rate=50,  # Puoi personalizzare
                activity_date=activity_date,
                description=f"Attività svolte nel Progetto : {subcustomer_name or project_id}"
            )
            if res:
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'OK'})
            else:
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'Errore inserimento'})
        except Exception as e:
            risultati.append({**r, 'subcustomer_name': subcustomer_name if 'subcustomer_name' in locals() else None, 'esito': f'Errore: {e}'})
    success_count = sum(1 for r in risultati if r.get('esito') == 'OK')
    error_count = len(risultati) - success_count
    return jsonify({
        'success': True,
        'message': f'Trasferimento completato: {success_count} OK, {error_count} errori',
        'report': risultati
    })

@app.route('/xml-to-csv.html')
def xml_to_csv():
    return render_template('xml-to-csv.html')

# Precompila la regex per estrarre percentuale IVA
percent_re = re.compile(r"(\d+)")

def parse_csv_to_bills(csv_data):
    f = io.StringIO(csv_data)
    reader = csv.DictReader(f)
    bills = []
    for row in reader:
        file_name = row.get('Filename', '')
        m = percent_re.search(row.get('LineTaxCode', ''))
        taxcode_id = get_taxcode_id(m.group(1)) if m else None
        bills.append({
            'vendor_id': row.get('Supplier', ''),
            'txn_date': row.get('BillDate', ''),
            'due_date': row.get('DueDate', ''),
            'ref_number': row.get('BillNo', ''),
            'memo': row.get('Memo', ''),
            'file_name': file_name,
            'taxcode_id': taxcode_id,
            'line_items': [{
                'amount': float(row.get('LineAmount', '0') or 0),
                'description': row.get('LineDescription', ''),
                'account_id': '1',
                'taxcode_id': taxcode_id
            }]
        })
    return bills

def bill_exists(importer, ref_number, vendor_id):
    """Check via QuickBooks query if a bill with same DocNumber and VendorRef exists"""
    import requests
    url = f"{importer.base_url}/v3/company/{importer.realm_id}/query"
    # URL-encode query
    q = f"SELECT * FROM Bill WHERE DocNumber = '{ref_number}' AND VendorRef = '{vendor_id}'"
    params = {'query': q}
    resp = requests.get(url, headers=importer.headers, params=params)
    if resp.status_code == 200:
        data = resp.json().get('QueryResponse', {})
        return bool(data.get('Bill'))
    return False

@app.route('/upload-to-qb', methods=['POST'])
def upload_to_qb():
    logging.info('START standard upload_to_qb')
    data = request.get_json()
    csv_data = data.get('csv')
    if not csv_data:
        logging.error('Nessun dato CSV ricevuto')
        return jsonify({'success': False, 'error': 'Nessun dato CSV ricevuto'}), 400
    # Parsing CSV
    bills = parse_csv_to_bills(csv_data)
    logging.info('Parsed %d bills from CSV (standard)', len(bills))
    # Inizializza importer e TokenManager
    from token_manager import TokenManager
    from quickbooks_bill_importer import QuickBooksBillImporter
    from config import API_BASE_URL, REALM_ID
    tm = TokenManager()
    importer = QuickBooksBillImporter(API_BASE_URL, REALM_ID, tm.get_access_token())

    # Risolvi vendor
    for bill in bills:
        name = bill['vendor_id']
        vid = importer.find_or_create_vendor(name)
        if vid:
            logging.info('Vendor resolved: %s -> %s', name, vid)
            bill['vendor_id'] = vid
        else:
            logging.error('Impossibile creare vendor: %s', name)
            return jsonify({'success': False, 'error': f"Impossibile creare vendor {name}"}), 500
    logging.info('Starting batch import of %d bills (standard)', len(bills))
    result = importer.batch_import_bills(bills)
    logging.info('Finished standard import: %d success, %d errors', result.get('success_count',0), result.get('error_count',0))
    # Se ci sono errori, restituisci success False e dettaglio errori
    if result['error_count'] > 0:
        return jsonify({'success': False, 'result': result, 'error': result['errors']})
    return jsonify({'success': True, 'result': result})

@app.route('/upload-to-qb-grouped', methods=['POST'])
def upload_to_qb_grouped():
    data = request.get_json()
    csv_data = data.get('csv')
    if not csv_data:
        return jsonify({'success': False, 'error': 'Nessun dato CSV ricevuto'}), 400
    group_by_vendor = bool(data.get('group_by_vendor', False))
    rules = data.get('grouping_rules', {})
    bills = parse_csv_to_bills(csv_data)
    from quickbooks_bill_importer import QuickBooksBillImporter
    from token_manager import TokenManager
    from config import API_BASE_URL, REALM_ID
    tm = TokenManager()
    importer = QuickBooksBillImporter(API_BASE_URL, REALM_ID, tm.get_access_token())

    bills_by_file = {}
    for b in bills:
        fname = b.get('file_name') or 'file'
        bills_by_file.setdefault(fname, []).append(b)

    results = []
    for fname, group in bills_by_file.items():
        bill0 = group[0]
        supplier = bill0['vendor_id']
        ref_number = bill0['ref_number']
        vid = importer.find_or_create_vendor(supplier)
        if not vid:
            results.append({
                'file': fname,
                'ref_number': ref_number,
                'supplier': supplier,
                'esito': 'errore',
                'dettaglio': f"Vendor creation failed for {supplier}"
            })
            continue
        exists = bill_exists(importer, ref_number, vid)
        if exists:
            results.append({
                'file': fname,
                'ref_number': ref_number,
                'supplier': supplier,
                'esito': 'saltata',
                'dettaglio': 'Fattura già presente in QB'
            })
            continue
        bill_data = {
            'vendor_id': vid,
            'ref_number': ref_number,
            'txn_date': bill0['txn_date'],
            'due_date': bill0['due_date'],
            'memo': bill0.get('memo'),
            # 'taxcode_id': bill0.get('taxcode_id'),  # RIMOSSO: il taxcode va solo sulle righe
            'line_items': []
        }
        for row in group:
            bill_data['line_items'].extend(row['line_items'])
        created = importer.create_bill(bill_data)
        if created and not created.get('error'):
            results.append({
                'file': fname,
                'ref_number': ref_number,
                'supplier': supplier,
                'esito': 'creata',
                'dettaglio': 'Fattura creata in QB'
            })
        else:
            err = created.get('error') if created else 'Unknown error'
            results.append({
                'file': fname,
                'ref_number': ref_number,
                'supplier': supplier,
                'esito': 'errore',
                'dettaglio': f"Errore creazione fattura: {err}"
            })

    # Log finale: un solo rigo per file
    import logging
    from collections import defaultdict
    summary_by_file = defaultdict(list)
    for r in results:
        summary_by_file[r['file']].append(r)    #logging.info('RISULTATO FINALE UPLOAD GROUPED:')
    for fname, items in summary_by_file.items():
        refs = ','.join(str(i['ref_number']) for i in items)
        sups = ','.join(str(i['supplier']) for i in items)
        esiti = set(i['esito'] for i in items)
        if len(esiti) == 1:
            esito = list(esiti)[0]
        else:
            esito = '/'.join(sorted(esiti))
        logging.info(f"File: {fname} | Fatt.: {refs} | Forn: {sups} | Esito: {esito}")
    
    return jsonify({'success': not any(r['esito'] == 'errore' for r in results), 'result': results})

@app.route('/performance-metrics', methods=['GET'])
def get_performance_metrics():
    """Endpoint per monitorare le metriche performance in tempo reale"""
    try:
        metrics = performance_monitor.get_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics,
            'message': 'Metriche performance recuperate con successo'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Errore nel recupero delle metriche'
        }), 500

@app.route('/performance-reset', methods=['POST'])
def reset_performance_metrics():
    """Reset delle metriche performance"""
    try:
        performance_monitor.reset_metrics()
        return jsonify({
            'success': True,
            'message': 'Metriche performance resettate con successo'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Errore nel reset delle metriche'
        }), 500

@app.route('/lista-progetti-paginati', methods=['POST'])
def lista_progetti_paginati():
    """Endpoint robusto: restituisce tutti i progetti che coprono il periodo richiesto, anche se più lento"""
    data = request.json
    try:
        import time
        start_time = time.time()
        page_size = min(data.get('pageSize', 20), 50)
        from_date = data.get('fromDate')
        to_date = data.get('toDate')
        project_number = data.get('projectNumber')
        print(f"[INFO] Robust: pageSize={page_size} {from_date} → {to_date} | projectNumber={project_number}")
        output = []
        if project_number:
            # Ricerca per numero progetto (ignora date)
            progetti = list_projects_by_number_full_unified(project_number)
        else:
            # Ricerca per data (default)
            progetti = list_projects_by_date_paginated_full_unified(from_date, to_date, page_size)
        print(f"[INFO] Progetti trovati: {len(progetti)}")
        for p in progetti:
            output.append({
                'id': p.get('id') or 'N/A',
                'number': p.get('number') or 'N/A',
                'name': p.get('name') or 'N/A',
                'cliente': p.get('contact_displayname') or '-',
                'manager_name': p.get('manager_name') or '-',
                'manager_email': p.get('manager_email') or '-',
                'project_value': p.get('project_value') or '0.00',
                'status': p.get('status') or 'UNKNOWN',
                'qb_import': p.get('qb_import') or '-',
                'equipment_period_from': p.get('equipment_period_from') or '-',
                'equipment_period_to': p.get('equipment_period_to') or '-',
                'project_type_name': p.get('project_type_name') or '-',
                'project_total_price': p.get('project_total_price') or '0.00'
            })
        duration = time.time() - start_time
        print(f"[INFO] ✅ ROBUST: Completato in {duration:.2f}s - {len(output)} progetti")
        response_data = {
            "projects": output,
            "pagination": {
                "page_size": page_size,
                "current_page": 1,
                "total_in_page": len(output),
            }
        }
        return jsonify(response_data)
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    print("🚀 Avvio Rentman Project Manager...")
    print("🔗 Import diretti:", 
          "✅ Fatture" if INVOICE_IMPORT_SUCCESS else "❌ Fatture (subprocess)", 
          "✅ Ore" if HOURS_IMPORT_SUCCESS else "❌ Ore (subprocess)")
    app.run(host="0.0.0.0", port=5000, debug=True)