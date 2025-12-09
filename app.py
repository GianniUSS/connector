from flask import Flask, request, jsonify, send_from_directory, render_template, session
from rentman_api import get_project_and_customer
from qb_customer import set_qb_import_status, get_qb_import_status
from create_or_update_invoice_for_project import create_or_update_invoice_for_project
from qb_time_activity import import_ore_da_excel, inserisci_ore
from qb_tracker import qb_tracker
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
from datetime import datetime
from quickbooks_taxcode_cache import get_taxcode_id
import logging
from token_manager import token_manager
import requests
import config
from db_config import save_bills_to_db, create_tables, test_connection, search_bills, get_bills_stats

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
app.secret_key = getattr(config, "APP_SECRET_KEY", os.getenv("APP_SECRET_KEY", "change-me"))

LOGIN_ENABLED = getattr(config, "APP_LOGIN_ENABLED", True)
LOGIN_USERNAME = getattr(config, "APP_LOGIN_USERNAME", "admin")
LOGIN_PASSWORD = getattr(config, "APP_LOGIN_PASSWORD", "password")

AUTH_WHITELIST = {
    '/',
    '/api/auth/login',
    '/api/auth/logout',
    '/api/auth/status',
    '/api/token-status',
    '/xml-to-csv.html',
    '/search-bills.html',
    '/delete-time-activities.html',
    '/excel-import-stats.html',
    '/webhook-manager.html',
    '/project-status-dashboard.html'
}


def is_authenticated():
    return bool(session.get('auth_user'))


@app.before_request
def require_login():
    if not LOGIN_ENABLED:
        return

    if request.method == 'OPTIONS':
        return

    path = request.path
    if path in AUTH_WHITELIST or path.startswith('/static'):
        return

    # Consenti favicon e file sorgente
    if path.endswith(('.ico', '.png', '.jpg', '.jpeg', '.svg', '.css', '.js')):
        return

    if is_authenticated():
        return

    if path.startswith('/api'):
        return jsonify({'success': False, 'authenticated': False, 'error': 'Autenticazione richiesta'}), 401

    return jsonify({'success': False, 'authenticated': False, 'error': 'Autenticazione richiesta'}), 401

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve file statici dalla cartella static"""
    return send_from_directory('static', path)


@app.route('/api/auth/status')
def auth_status():
    return jsonify({
        'authenticated': is_authenticated(),
        'loginEnabled': LOGIN_ENABLED,
        'user': session.get('auth_user')
    })


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    if not LOGIN_ENABLED:
        session['auth_user'] = 'disabled'
        return jsonify({'success': True, 'authenticated': True, 'loginEnabled': False})

    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if username == LOGIN_USERNAME and password == LOGIN_PASSWORD:
        session['auth_user'] = username
        return jsonify({'success': True, 'authenticated': True})

    return jsonify({'success': False, 'authenticated': False, 'error': 'Credenziali non valide'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    session.pop('auth_user', None)
    return jsonify({'success': True, 'authenticated': False})

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
                    
                    # Aggiorna sia il sistema legacy che il nuovo tracker
                    set_qb_import_status(project_id, status, result.get('message') or None)
                    qb_tracker.set_invoice_status(
                        project_id=project_id,
                        status=status,
                        message=result.get('message') or 'Fattura elaborata con successo',
                        details={
                            'processing_method': 'direct_import',
                            'is_simulated': is_simulated,
                            'qb_response': result.get('qb_response'),
                            'invoice_id': result.get('invoice_id'),
                            'amount': result.get('amount')
                        }
                    )
                    
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
                    # Aggiorna sia il sistema legacy che il nuovo tracker
                    set_qb_import_status(project_id, 'error', result.get('error', 'Errore sconosciuto'))
                    qb_tracker.set_invoice_status(
                        project_id=project_id,
                        status='error',
                        message=result.get('error', 'Errore sconosciuto'),
                        details={
                            'processing_method': 'direct_import',
                            'error_details': result.get('error_details'),
                            'qb_response': result.get('qb_response')
                        }
                    )
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
                    qb_tracker.set_invoice_status(
                        project_id=project_id,
                        status='success',
                        message='Fattura elaborata tramite subprocess',
                        details={
                            'processing_method': 'subprocess',
                            'stdout': result.stdout
                        }
                    )
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'success',
                        'output': result.stdout,
                        'error': None
                    }
                else:
                    set_qb_import_status(project_id, 'error', result.stderr)
                    qb_tracker.set_invoice_status(
                        project_id=project_id,
                        status='error',
                        message='Errore durante elaborazione subprocess',
                        details={
                            'processing_method': 'subprocess',
                            'stderr': result.stderr,
                            'stdout': result.stdout,
                            'return_code': result.returncode
                        }
                    )
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'error',
                        'output': result.stdout,
                        'error': result.stderr
                    }
        except subprocess.TimeoutExpired:
            set_qb_import_status(project_id, 'timeout', 'Timeout dopo 2 minuti')
            qb_tracker.set_invoice_status(
                project_id=project_id,
                status='timeout',
                message='Timeout durante elaborazione subprocess',
                details={
                    'processing_method': 'subprocess',
                    'timeout_seconds': 120
                }
            )
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': 'timeout',
                'output': '',
                'error': 'Timeout dopo 2 minuti'
            }
        except Exception as e:
            set_qb_import_status(project_id, 'error', str(e))
            qb_tracker.set_invoice_status(
                project_id=project_id,
                status='error',
                message=f'Errore generico: {str(e)}',
                details={
                    'processing_method': 'subprocess',
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                }
            )
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
    
    # Costruisci il messaggio di risposta
    message = f"Elaborazione completata: {success_count} fatture create"
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
    """Endpoint per importare ore lavorate da file Excel e inserirle automaticamente in QuickBooks"""
    logging.info("INIZIO IMPORTAZIONE ORE DA EXCEL")
    
    if 'excelFile' not in request.files:
        logging.error("ERRORE: File Excel mancante nella richiesta")
        return jsonify({'success': False, 'error': 'File Excel mancante'}), 400
    
    file = request.files['excelFile']
    data_attivita = request.form.get('data_attivita')
    
    logging.info(f"File ricevuto: {file.filename}")
    logging.info(f"Data attivita: {data_attivita}")
    
    if not data_attivita:
        logging.error("ERRORE: Data attivita mancante")
        return jsonify({'success': False, 'error': 'Data attività mancante'}), 400
    
    if file.filename == '':
        logging.error("ERRORE: Nessun file selezionato")
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    
    try:
        logging.info("Salvataggio file temporaneo...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            file.save(tmp.name)
            tmp_filepath = tmp.name
        
        logging.info(f"File temporaneo creato: {tmp_filepath}")
        logging.info("Avvio elaborazione Excel...")
        
        report = import_ore_da_excel(tmp_filepath, data_attivita)
        
        # Rimuovi file temporaneo
        try:
            import os
            os.remove(tmp_filepath)
            logging.info("File temporaneo rimosso")
        except Exception as e:
            logging.warning(f"ATTENZIONE: Impossibile rimuovere file temporaneo: {e}")
        
        success_count = sum(1 for r in report if r.get('esito') == 'OK')
        error_count = len(report) - success_count
        
        logging.info(f"VALIDAZIONE EXCEL COMPLETATA:")
        logging.info(f"   Totale righe elaborate: {len(report)}")
        logging.info(f"   Successi: {success_count}")
        logging.info(f"   Errori: {error_count}")
        
        # Log dettaglio errori se presenti
        if error_count > 0:
            errori = [r for r in report if r.get('esito') != 'OK']
            for err in errori[:5]:  # Mostra max 5 errori nel log
                logging.warning(f"   Errore riga {err.get('row', '?')}: {err.get('esito', 'N/A')}")
            if len(errori) > 5:
                logging.warning(f"   ... e altri {len(errori) - 5} errori")
        
        # Se ci sono righe valide, procedi automaticamente con l'inserimento in QuickBooks
        qb_success_count = 0
        qb_error_count = 0
        qb_results = []
        
        # Traccia l'inizio dell'importazione Excel
        import datetime as dt
        excel_import_key = f"excel_import_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        qb_tracker.set_excel_import_status(
            import_type='hours',
            key=excel_import_key,
            status='started',
            message=f'Avvio importazione Excel: {success_count} righe valide',
            details={
                'file_name': file.filename,
                'activity_date': data_attivita,
                'total_rows': len(report),
                'valid_rows': success_count,
                'error_rows': error_count,
                'validation_report': report[:10]  # Prime 10 righe per debug
            }
        )
        
        if success_count > 0:
            logging.info(f"AVVIO INSERIMENTO AUTOMATICO IN QUICKBOOKS per {success_count} righe valide...")
            
            righe_valide = [r for r in report if r.get('esito') == 'OK']
            
            for idx, r in enumerate(righe_valide, 1):
                logging.info(f"Inserimento QB {idx}/{len(righe_valide)}: Project {r.get('project_id')}")
                
                try:
                    # Recupera dati progetto/cliente da Rentman
                    project_id = r.get('project_id')
                    project_data = get_project_and_customer(project_id)
                    project = project_data['project']
                    customer = project_data['customer']
                    
                    # Mapping dati
                    from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
                    customer_data = map_rentman_to_qbo_customer(customer)
                    subcustomer_data = map_rentman_to_qbo_subcustomer(project)
                    
                    # Trova/crea customer e subcustomer in QB
                    from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
                    qb_customer = trova_o_crea_customer(customer_data["DisplayName"], customer_data)
                    if not qb_customer or not qb_customer.get("Id"):
                        raise Exception(f"Customer non trovato/creato per {customer_data.get('DisplayName')}")
                    
                    qb_subcustomer = trova_o_crea_subcustomer(subcustomer_data["DisplayName"], qb_customer["Id"], subcustomer_data)
                    if not qb_subcustomer or not qb_subcustomer.get("Id"):
                        raise Exception(f"Subcustomer non trovato/creato per {subcustomer_data.get('DisplayName')}")
                    
                    # Inserisci timeactivity in QuickBooks
                    qb_result = inserisci_ore(
                        employee_name=r.get('employee_name'),
                        subcustomer_id=qb_subcustomer["Id"],
                        hours=r.get('hours'),
                        minutes=r.get('minutes'),
                        hourly_rate=50,  # Tariffa oraria di default
                        activity_date=data_attivita,
                        description=f"Import Excel - Project {project_id}"
                    )
                    
                    if qb_result:
                        qb_success_count += 1
                        qb_results.append({"project_id": project_id, "employee": r.get('employee_name'), "esito": "SUCCESS"})
                        logging.info(f"   SUCCESS: TimeActivity inserita per Project {project_id}")
                        
                        # Traccia il successo dell'importazione ore
                        qb_tracker.set_time_activity_status(
                            project_id=project_id,
                            employee_name=r.get('employee_name'),
                            status='success',
                            message=f"Importate {r.get('hours')}h {r.get('minutes')}m",
                            details={
                                'hours': r.get('hours'),
                                'minutes': r.get('minutes'),
                                'activity_date': data_attivita,
                                'import_method': 'excel_auto',
                                'qb_timeactivity_id': qb_result.get('TimeActivity', {}).get('Id') if isinstance(qb_result, dict) else None
                            }
                        )
                    else:
                        qb_error_count += 1
                        qb_results.append({"project_id": project_id, "employee": r.get('employee_name'), "esito": "ERRORE QB"})
                        logging.error(f"   ERRORE: Inserimento QB fallito per Project {project_id}")
                        
                        # Traccia l'errore dell'importazione ore
                        qb_tracker.set_time_activity_status(
                            project_id=project_id,
                            employee_name=r.get('employee_name'),
                            status='error',
                            message="Errore inserimento in QuickBooks",
                            details={
                                'hours': r.get('hours'),
                                'minutes': r.get('minutes'),
                                'activity_date': data_attivita,
                                'import_method': 'excel_auto',
                                'error_type': 'qb_insertion_failed'
                            }
                        )
                
                except Exception as e:
                    qb_error_count += 1
                    qb_results.append({"project_id": r.get('project_id'), "employee": r.get('employee_name'), "esito": f"ERRORE: {str(e)}"})
                    logging.error(f"   ERRORE durante inserimento QB Project {r.get('project_id')}: {str(e)}")
                    
                    # Traccia l'errore generico
                    qb_tracker.set_time_activity_status(
                        project_id=r.get('project_id'),
                        employee_name=r.get('employee_name'),
                        status='error',
                        message=f"Errore: {str(e)[:100]}",
                        details={
                            'hours': r.get('hours'),
                            'minutes': r.get('minutes'),
                            'activity_date': data_attivita,
                            'import_method': 'excel_auto',
                            'error_type': 'general_error',
                            'full_error': str(e)
                        }
                    )
            
            logging.info(f"INSERIMENTO QUICKBOOKS COMPLETATO:")
            logging.info(f"   Righe inserite con successo: {qb_success_count}")
            logging.info(f"   Righe con errori QB: {qb_error_count}")
        
        # Aggiorna il tracciamento Excel con il risultato finale
        final_status = 'success' if qb_success_count == success_count else ('partial' if qb_success_count > 0 else 'error')
        qb_tracker.set_excel_import_status(
            import_type='hours',
            key=excel_import_key,
            status=final_status,
            message=f'Importazione completata: {qb_success_count}/{success_count} righe inserite',
            details={
                'file_name': file.filename,
                'activity_date': data_attivita,
                'validation_results': {
                    'total_rows': len(report),
                    'valid_rows': success_count,
                    'error_rows': error_count
                },
                'qb_results': {
                    'success_count': qb_success_count,
                    'error_count': qb_error_count,
                    'success_rate': f"{(qb_success_count/success_count)*100:.1f}%" if success_count > 0 else "0%"
                },
                'detailed_results': qb_results
            }
        )
        
        # Messaggio finale dettagliato
        if success_count == 0:
            final_message = f"Nessuna riga valida trovata nel file Excel ({error_count} errori)"
        elif qb_success_count == success_count:
            final_message = f"Importazione completata con successo: {qb_success_count} ore inserite in QuickBooks"
        elif qb_success_count > 0:
            final_message = f"Importazione parziale: {qb_success_count} ore inserite, {qb_error_count} errori QB"
        else:
            final_message = f"Validazione OK ({success_count} righe), ma errori nell'inserimento QB"
        
        return jsonify({
            'success': True,
            'message': final_message,
            'report': report,
            'qb_results': qb_results,
            'stats': {
                'validation_success': success_count,
                'validation_errors': error_count,
                'qb_success': qb_success_count,
                'qb_errors': qb_error_count
            }
        })
    except Exception as e:
        logging.error(f"ERRORE DURANTE IMPORTAZIONE: {str(e)}")
        logging.error(f"   File: {file.filename}")
        logging.error(f"   Data: {data_attivita}")
        
        # Traccia l'errore generale dell'importazione Excel
        try:
            import datetime as dt
            qb_tracker.set_excel_import_status(
                import_type='hours',
                key=f"excel_import_error_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                status='error',
                message=f'Errore durante importazione Excel: {str(e)[:100]}',
                details={
                    'file_name': file.filename,
                    'activity_date': data_attivita,
                    'error_type': 'general_exception',
                    'full_error': str(e),
                    'exception_type': type(e).__name__
                }
            )
        except Exception as tracker_err:
            logging.warning(f"Errore nel tracciamento: {tracker_err}")
        
        return jsonify({'success': False, 'error': str(e)})

@app.route('/trasferisci-ore-qb', methods=['POST'])
def trasferisci_ore_qb():
    """Endpoint per trasferire le righe OK su QuickBooks, mostrando anche il nome sub-customer"""
    logging.info("INIZIO TRASFERIMENTO ORE A QUICKBOOKS")
    
    data = request.get_json()
    rows = data.get('rows', [])
    
    if not rows:
        logging.error("ERRORE: Nessuna riga da trasferire")
        return jsonify({'success': False, 'error': 'Nessuna riga da trasferire'}), 400
    
    logging.info(f"Righe da trasferire: {len(rows)}")
    
    risultati = []
    for idx, r in enumerate(rows, 1):
        logging.info(f"Elaborando riga {idx}/{len(rows)}: Project {r.get('project_id')}")
        
        try:
            # Recupera nome sub-customer da Rentman e dati progetto/cliente
            project_id = r.get('project_id')
            subcustomer_name = None
            qb_customer = None
            qb_subcustomer = None
            
            logging.debug(f"   Recupero dati progetto {project_id}...")
            
            try:
                # Ottieni i dati completi da Rentman
                project_data = get_project_and_customer(project_id)
                project = project_data['project']
                customer = project_data['customer']
                subcustomer_name = project.get('name')
                
                logging.debug(f"   Dati progetto ottenuti: {subcustomer_name}")
                
                # Mapping dati
                from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
                customer_data = map_rentman_to_qbo_customer(customer)
                subcustomer_data = map_rentman_to_qbo_subcustomer(project)
                
                logging.debug(f"   Mapping completato - Customer: {customer_data.get('DisplayName')}")
                
                # Trova/crea customer e subcustomer in QB
                from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
                qb_customer = trova_o_crea_customer(customer_data["DisplayName"], customer_data)
                if not qb_customer or not qb_customer.get("Id"):
                    raise Exception("Customer non trovato/creato")
                
                logging.debug(f"   Customer QB: {qb_customer.get('Id')}")
                
                qb_subcustomer = trova_o_crea_subcustomer(subcustomer_data["DisplayName"], qb_customer["Id"], subcustomer_data)
                if not qb_subcustomer or not qb_subcustomer.get("Id"):
                    raise Exception("Sub-customer non trovato/creato")
                
                logging.debug(f"   Sub-customer QB: {qb_subcustomer.get('Id')}")
                
                # Estrai la data di fine progetto (planperiod_end) da Rentman
                activity_date = project.get("planperiod_end")
                if activity_date:
                    activity_date = str(activity_date)[:10]
                    logging.debug(f"   Data attivita: {activity_date}")
                else:
                    logging.error(f"   ERRORE: Data fine progetto mancante per progetto {project_id}")
                    risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'Errore: data fine progetto mancante'})
                    continue
                    
            except Exception as e:
                logging.error(f"   ERRORE dati progetto/cliente {project_id}: {e}")
                subcustomer_name = subcustomer_name or None
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': f'Errore dati progetto/cliente: {e}'})
                continue
            
            # Effettua la chiamata a QB usando l'ID corretto del sub-customer e la data estratta
            hours = int(r.get('hours', 0))
            minutes = int(r.get('minutes', 0))
            employee_name = r.get('employee_name')
            
            logging.info(f"   Invio a QB: {employee_name} - {hours}h {minutes}m per progetto {subcustomer_name}")
            
            res = inserisci_ore(
                employee_name=employee_name,
                subcustomer_id=qb_subcustomer["Id"],
                hours=hours,
                minutes=minutes,
                hourly_rate=50,  # Puoi personalizzare
                activity_date=activity_date,
                description=f"Attività svolte nel Progetto : {subcustomer_name or project_id}"
            )
            
            if res:
                logging.info(f"   SUCCESS: Riga {idx} trasferita con successo")
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'OK'})
                
                # Traccia il successo dell'importazione ore
                qb_tracker.set_time_activity_status(
                    project_id=project_id,
                    employee_name=employee_name,
                    status='success',
                    message=f"Trasferite {hours}h {minutes}m",
                    details={
                        'hours': hours,
                        'minutes': minutes,
                        'activity_date': activity_date,
                        'import_method': 'manual_transfer',
                        'subcustomer_name': subcustomer_name,
                        'qb_timeactivity_id': res.get('TimeActivity', {}).get('Id') if isinstance(res, dict) else None
                    }
                )
            else:
                logging.error(f"   ERRORE: Riga {idx} errore inserimento QB")
                risultati.append({**r, 'subcustomer_name': subcustomer_name, 'esito': 'Errore inserimento'})
                
                # Traccia l'errore dell'importazione ore
                qb_tracker.set_time_activity_status(
                    project_id=project_id,
                    employee_name=employee_name,
                    status='error',
                    message="Errore inserimento in QuickBooks",
                    details={
                        'hours': hours,
                        'minutes': minutes,
                        'activity_date': activity_date,
                        'import_method': 'manual_transfer',
                        'subcustomer_name': subcustomer_name,
                        'error_type': 'qb_insertion_failed'
                    }
                )
                
        except Exception as e:
            logging.error(f"   ERRORE generico riga {idx}: {e}")
            risultati.append({**r, 'subcustomer_name': subcustomer_name if 'subcustomer_name' in locals() else None, 'esito': f'Errore: {e}'})
            
            # Traccia l'errore generico
            if 'project_id' in locals() and 'employee_name' in locals():
                qb_tracker.set_time_activity_status(
                    project_id=project_id,
                    employee_name=employee_name,
                    status='error',
                    message=f"Errore: {str(e)[:100]}",
                    details={
                        'hours': r.get('hours', 0),
                        'minutes': r.get('minutes', 0),
                        'import_method': 'manual_transfer',
                        'error_type': 'general_error',
                        'full_error': str(e)
                    }
                )
    
    success_count = sum(1 for r in risultati if r.get('esito') == 'OK')
    error_count = len(risultati) - success_count
    
    logging.info(f"TRASFERIMENTO COMPLETATO:")
    logging.info(f"   Totale righe elaborate: {len(risultati)}")
    logging.info(f"   Successi: {success_count}")
    logging.info(f"   Errori: {error_count}")
    
    # Log dettaglio errori se presenti
    if error_count > 0:
        errori = [r for r in risultati if r.get('esito') != 'OK']
        for err in errori[:3]:  # Mostra max 3 errori nel log
            logging.warning(f"   Errore Project {err.get('project_id', '?')}: {err.get('esito', 'N/A')}")
        if len(errori) > 3:
            logging.warning(f"   ... e altri {len(errori) - 3} errori")
    
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

def safe_float_conversion(value):
    """Converte in modo sicuro un valore in float, restituendo 0.0 se la conversione fallisce"""
    if not value or str(value).strip() == '':
        return 0.0
    try:
        # Rimuove spazi e caratteri non numerici comuni
        cleaned_value = str(value).strip().replace(',', '.')
        # Prova a estrarre solo i numeri (incluso il punto decimale)
        import re
        numeric_match = re.match(r'^-?\d*\.?\d*', cleaned_value)
        if numeric_match and numeric_match.group():
            return float(numeric_match.group())
        else:
            return 0.0
    except (ValueError, TypeError):
        return 0.0

def parse_csv_to_bills(csv_data):
    f = io.StringIO(csv_data)
    reader = csv.DictReader(f)
    default_item_id = getattr(config, 'DEFAULT_QB_ITEM_ID', None)
    if default_item_id:
        default_item_id = str(default_item_id).strip() or None
    
    # Raggruppa righe per (Supplier, BillNo)
    bills_dict = {}
    
    for row in reader:
        file_name = row.get('Filename', '')
        supplier = row.get('Supplier', '')
        bill_no = row.get('BillNo', '')
        
        # Chiave univoca per raggruppare
        key = (supplier, bill_no)
        
        m = percent_re.search(row.get('LineTaxCode', ''))
        tax_percent = m.group(1) if m else None
        taxcode_id = get_taxcode_id(tax_percent) if tax_percent else None
        amount = safe_float_conversion(row.get('LineAmount', '0'))
        quantity_raw = row.get('Quantity')
        unit_price_raw = row.get('UnitPrice')
        quantity = None
        unit_price = None
        if quantity_raw is not None and str(quantity_raw).strip() != '':
            quantity = safe_float_conversion(quantity_raw)
        if unit_price_raw is not None and str(unit_price_raw).strip() != '':
            unit_price = safe_float_conversion(unit_price_raw)
        if unit_price is None and quantity not in (None, 0):
            try:
                unit_price = round(amount / quantity, 5)
            except ZeroDivisionError:
                unit_price = None
        item_name = row.get('ProductService') or row.get('ItemName') or row.get('LineDescription')
        line_item = {
            'amount': amount,
            'description': row.get('LineDescription', ''),
            'account_id': '1',
            'taxcode_id': taxcode_id,
            'tax_percent': tax_percent
        }
        if quantity is not None:
            line_item['quantity'] = quantity
        if unit_price is not None:
            line_item['unit_price'] = unit_price
        if default_item_id:
            line_item['item_id'] = default_item_id
        if item_name:
            line_item['item_name'] = item_name.strip()
        
        # Se la fattura non esiste ancora, creala
        if key not in bills_dict:
            bills_dict[key] = {
                'vendor_id': supplier,
                'txn_date': row.get('BillDate', ''),
                'due_date': row.get('DueDate', ''),
                'ref_number': bill_no,
                'memo': row.get('Memo', ''),
                'file_name': file_name,
                'taxcode_id': taxcode_id,
                'line_items': []
            }
        
        # Aggiungi la riga alla fattura esistente
        bills_dict[key]['line_items'].append(line_item)
    
    # Converti il dizionario in lista
    bills = list(bills_dict.values())
    logging.info('📋 Raggruppate %d fatture da %d righe CSV', len(bills), sum(len(b['line_items']) for b in bills))
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
    update_existing = bool(data.get('update_existing') or data.get('allow_update'))
    logging.info('🔧 FLAG update_existing ricevuto: %s (data.get: update_existing=%s, allow_update=%s)', 
                 update_existing, data.get('update_existing'), data.get('allow_update'))
    created_docs = []
    updated_docs = []
    skipped_docs = []
    errors = []
    bills_to_create = []

    for bill in bills:
        ref_number = bill.get('ref_number')
        existing_bill = None
        if ref_number:
            existing_bill = importer.find_bill_by_docnumber(bill['vendor_id'], ref_number)
        if existing_bill:
            doc_number = existing_bill.get('DocNumber') or ref_number or existing_bill.get('Id')
            logging.info("Bill già presente in QuickBooks: vendor=%s ref=%s (Id=%s)", bill['vendor_id'], ref_number, existing_bill.get('Id'))
            if update_existing:
                logging.info("🔄 Tentativo di AGGIORNAMENTO per Bill DocNumber=%s (Id=%s)", doc_number, existing_bill.get('Id'))
                update_result = importer.update_bill(existing_bill.get('Id'), existing_bill.get('SyncToken'), bill)
                if update_result and not update_result.get('error'):
                    logging.info("✅ Bill %s aggiornata con successo", doc_number)
                    updated_docs.append(doc_number)
                else:
                    error_detail = update_result.get('error') if isinstance(update_result, dict) else update_result
                    logging.error("❌ Aggiornamento fallito per Bill %s: %s", doc_number, error_detail)
                    errors.append(f"Aggiornamento fallito per {doc_number}: {error_detail}")
            else:
                logging.info("⏭️ Bill %s SALTATA (update_existing=False)", doc_number)
                skipped_docs.append(doc_number)
        else:
            bills_to_create.append(bill)

    logging.info('Starting creation of %d new bills (standard)', len(bills_to_create))
    create_result = None
    if bills_to_create:
        create_result = importer.batch_import_bills(bills_to_create)
        logging.info('Finished standard import: %d success, %d errors', create_result.get('success_count', 0), create_result.get('error_count', 0))
        if create_result.get('created_bills'):
            for created_bill in create_result['created_bills']:
                bill_entity = created_bill.get('Bill') if isinstance(created_bill, dict) else None
                if isinstance(bill_entity, list) and bill_entity:
                    bill_entity = bill_entity[0]
                if isinstance(bill_entity, dict):
                    doc_number = bill_entity.get('DocNumber') or bill_entity.get('DocNum') or bill_entity.get('Id')
                    if doc_number:
                        created_docs.append(doc_number)
        for err in create_result.get('errors', []):
            errors.append(err)
    else:
        logging.info('Nessuna nuova fattura da creare (tutte trovate esistenti)')

    total_created = len(created_docs)
    total_updated = len(updated_docs)
    total_skipped = len(skipped_docs)
    total_errors = len(errors)
    summary_parts = [
        f"create: {total_created}",
        f"aggiornate: {total_updated}",
        f"saltate: {total_skipped}",
        f"errori: {total_errors}"
    ]
    message = "Import QuickBooks completato - " + ", ".join(summary_parts)

    result_payload = {
        'created': created_docs,
        'updated': updated_docs,
        'skipped': skipped_docs,
        'errors': errors
    }

    success = total_errors == 0
    response = {
        'success': success,
        'message': message,
        'result': result_payload
    }

    status_code = 200 if success else 207
    return jsonify(response), status_code

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

@app.route('/save-to-database', methods=['POST'])
def save_to_database():
    """Endpoint per salvare i dati CSV nel database MySQL"""
    try:
        data = request.get_json()
        csv_data = data.get('csvData')
        
        if not csv_data:
            return jsonify({'success': False, 'message': 'Nessun dato CSV fornito'})
        
        # Testa la connessione al database
        connection_ok, connection_msg = test_connection()
        if not connection_ok:
            logging.error(f"Errore connessione database: {connection_msg}")
            return jsonify({'success': False, 'message': f'Errore connessione database: {connection_msg}'})
        
        # Crea le tabelle se non esistono
        if not create_tables():
            return jsonify({'success': False, 'message': 'Errore creazione tabelle nel database'})
        
        # Converte CSV in lista di dizionari
        bills_data = []
        f = io.StringIO(csv_data)
        reader = csv.DictReader(f)
        
        for row in reader:
            bills_data.append(row)
        
        if not bills_data:
            return jsonify({'success': False, 'message': 'Nessun dato valido nel CSV'})
        
        # Salva nel database
        success, message = save_bills_to_db(bills_data)
        
        if success:
            logging.info(f"Salvati {len(bills_data)} record nel database")
            return jsonify({'success': True, 'message': message})
        else:
            logging.error(f"Errore salvataggio database: {message}")
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        error_msg = f"Errore interno durante il salvataggio: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'message': error_msg})

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
    
@app.route('/search-bills.html')
def search_bills_page():
    """Serve la pagina di ricerca fatture"""
    return render_template('search-bills.html')

@app.route('/search-bills', methods=['POST'])
def search_bills_api():
    """API per la ricerca delle fatture nel database"""
    try:
        data = request.get_json()
        
        # Validazione dei dati in input
        if not data:
            return jsonify({'success': False, 'message': 'Nessun dato ricevuto nella richiesta'})
        
        # Estrai parametri di ricerca con validazione
        search_term = str(data.get('search_term', '')).strip()
        date_from = str(data.get('date_from', '')).strip()
        date_to = str(data.get('date_to', '')).strip()
        supplier = str(data.get('supplier', '')).strip()
        amount_min = str(data.get('amount_min', '')).strip()
        amount_max = str(data.get('amount_max', '')).strip()
        
        # Conversione sicura degli interi
        try:
            page = int(data.get('page', 1))
        except (ValueError, TypeError):
            page = 1
            
        try:
            per_page = int(data.get('per_page', 50))
        except (ValueError, TypeError):
            per_page = 50
        
        # Valida parametri
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50
              # Converte date vuote in None
        date_from = date_from if date_from else None
        date_to = date_to if date_to else None
        
        # Conversione sicura degli importi
        try:
            amount_min = float(amount_min) if amount_min else None
        except (ValueError, TypeError):
            amount_min = None
            
        try:
            amount_max = float(amount_max) if amount_max else None
        except (ValueError, TypeError):
            amount_max = None
        
        # Esegui la ricerca
        success, message, results, total_count, total_pages, all_results = search_bills(
            search_term=search_term,
            date_from=date_from,
            date_to=date_to,
            supplier=supplier,
            amount_min=amount_min,
            amount_max=amount_max,
            page=page,
            per_page=per_page
        )
        
        if success:
            logging.info(f"Ricerca eseguita: {len(results)} risultati in pagina {page}, totale {total_count}")
            return jsonify({
                'success': True,
                'data': results,
                'total': total_count,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
                'all_data': all_results  # Per export CSV
            })
        else:
            logging.error(f"Errore ricerca fatture: {message}")
            return jsonify({'success': False, 'message': message})
            
    except ValueError as e:
        error_msg = f"Parametri non validi: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'message': error_msg})
    except Exception as e:
        error_msg = f"Errore interno durante la ricerca: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'message': error_msg})

@app.route('/bills-stats', methods=['GET'])
def bills_stats_api():
    """API per ottenere statistiche della tabella bills"""
    try:
        stats = get_bills_stats()
        
        if stats:
            # Formatta le statistiche per la risposta
            formatted_stats = {
                'total_bills': stats['total_bills'],
                'unique_suppliers': stats['unique_suppliers'],
                'earliest_date': stats['earliest_date'].isoformat() if stats['earliest_date'] else None,
                'latest_date': stats['latest_date'].isoformat() if stats['latest_date'] else None,
                'total_amount': float(stats['total_amount']) if stats['total_amount'] else 0,
                'avg_amount': float(stats['avg_amount']) if stats['avg_amount'] else 0
            }
            
            logging.info(f"Statistiche fatture: {stats['total_bills']} fatture totali")
            return jsonify({'success': True, 'stats': formatted_stats})
        else:
            return jsonify({'success': False, 'message': 'Impossibile ottenere statistiche'})
            
    except Exception as e:
        error_msg = f"Errore ottenendo statistiche: {str(e)}"
        logging.error(error_msg)
        return jsonify({'success': False, 'message': error_msg})

@app.route('/elimina-ore-qb', methods=['POST'])
def elimina_ore_qb():
    """Endpoint per eliminare TimeActivity da QuickBooks"""
    logging.info("INIZIO ELIMINAZIONE ORE DA QUICKBOOKS")
    
    data = request.get_json()
    
    # Parametri di filtro
    customer_id = data.get('customer_id')
    project_name = data.get('project_name')  # NUOVO: supporto per nome progetto
    employee_name = data.get('employee_name')
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    date_exact = data.get('date_exact')
    preview_only = data.get('preview_only', False)
    
    logging.info(f"Filtri eliminazione:")
    logging.info(f"  Customer ID: {customer_id}")
    logging.info(f"  Nome Progetto: {project_name}")
    logging.info(f"  Employee: {employee_name}")
    logging.info(f"  Data esatta: {date_exact}")
    logging.info(f"  Data da: {date_from}")
    logging.info(f"  Data a: {date_to}")
    logging.info(f"  Solo anteprima: {preview_only}")
    
    try:
        # Inizializza connessione QuickBooks
        token_manager.load_refresh_token()
        access_token = token_manager.get_access_token()
        
        if access_token == "invalid_token_handled_gracefully":
            return jsonify({
                'success': False,
                'error': 'Token QuickBooks non valido. Aggiorna il token prima di continuare.'
            })
        
        # Costruisci query per trovare TimeActivity
        url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        query = "SELECT * FROM TimeActivity"
        where_conditions = []
        found_customer_name = None
        
        if customer_id:
            where_conditions.append(f"CustomerRef = '{customer_id}'")
        
        if project_name:
            # Trova Customer ID per nome progetto
            found_customer_id, found_customer_name = find_customer_by_project_name_web(access_token, project_name)
            if found_customer_id:
                where_conditions.append(f"CustomerRef = '{found_customer_id}'")
                logging.info(f"Filtro per progetto '{project_name}' -> Customer: {found_customer_name} (ID: {found_customer_id})")
            else:
                return jsonify({
                    'success': False,
                    'error': f"Progetto '{project_name}' non trovato nei Customer QuickBooks"
                })
        
        if employee_name:
            # Trova employee ID
            emp_query = f"SELECT * FROM Employee WHERE DisplayName = '{employee_name}'"
            emp_response = requests.get(url, headers=headers, params={"query": emp_query})
            if emp_response.status_code == 200:
                emp_data = emp_response.json().get("QueryResponse", {}).get("Employee", [])
                if emp_data:
                    if not isinstance(emp_data, list):
                        emp_data = [emp_data]
                    emp_id = emp_data[0]["Id"]
                    where_conditions.append(f"EmployeeRef = '{emp_id}'")
                    logging.info(f"Employee '{employee_name}' trovato con ID: {emp_id}")
                else:
                    return jsonify({
                        'success': False,
                        'error': f"Employee '{employee_name}' non trovato"
                    })
        
        if date_exact:
            where_conditions.append(f"TxnDate = '{date_exact}'")
        else:
            if date_from:
                where_conditions.append(f"TxnDate >= '{date_from}'")
            if date_to:
                where_conditions.append(f"TxnDate <= '{date_to}'")
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += " ORDER BY TxnDate DESC"
        
        logging.info(f"Query TimeActivity: {query}")
        
        # Trova TimeActivity
        response = requests.get(url, headers=headers, params={"query": query})
        
        if response.status_code != 200:
            logging.error(f"Errore ricerca TimeActivity: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f"Errore ricerca TimeActivity: {response.status_code}"
            })
        
        data_response = response.json()
        activities = data_response.get("QueryResponse", {}).get("TimeActivity", [])
        
        # Normalizza in lista
        if not isinstance(activities, list):
            activities = [activities] if activities else []
        
        logging.info(f"Trovate {len(activities)} TimeActivity da elaborare")
        
        if not activities:
            return jsonify({
                'success': True,
                'message': 'Nessuna TimeActivity trovata con i filtri specificati',
                'activities_found': [],
                'deleted_count': 0
            })
        
        # Prepara lista attività per risposta
        activities_found = []
        for activity in activities:
            emp_ref = activity.get("EmployeeRef", {})
            emp_name = emp_ref.get("name", "N/A") if isinstance(emp_ref, dict) else "N/A"
            
            activities_found.append({
                'id': activity.get("Id"),
                'date': activity.get("TxnDate"),
                'employee': emp_name,
                'hours': activity.get("Hours", 0),
                'minutes': activity.get("Minutes", 0),
                'description': activity.get("Description", "")
            })
        
        # Se è solo anteprima, restituisci i risultati senza eliminare
        if preview_only:
            return jsonify({
                'success': True,
                'message': f'Anteprima: trovate {len(activities)} TimeActivity',
                'activities_found': activities_found,
                'deleted_count': 0,
                'preview': True
            })
        
        # Procedi con eliminazione
        headers["Content-Type"] = "application/json"
        success_count = 0
        error_count = 0
        deleted_activities = []
        
        for activity in activities:
            activity_id = activity["Id"]
            sync_token = activity["SyncToken"]
            
            delete_url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/timeactivity?operation=delete"
            payload = {
                "Id": activity_id,
                "SyncToken": sync_token
            }
            
            try:
                del_resp = requests.post(delete_url, headers=headers, json=payload)
                if del_resp.status_code in [200, 201]:
                    success_count += 1
                    deleted_activities.append(activity_id)
                    logging.info(f"✅ Eliminata TimeActivity ID: {activity_id}")
                else:
                    error_count += 1
                    logging.error(f"❌ Errore eliminazione ID {activity_id}: {del_resp.status_code}")
            except Exception as e:
                error_count += 1
                logging.error(f"❌ Errore eliminazione ID {activity_id}: {e}")
        
        logging.info(f"ELIMINAZIONE COMPLETATA:")
        logging.info(f"  Eliminate: {success_count}")
        logging.info(f"  Errori: {error_count}")
        
        return jsonify({
            'success': True,
            'message': f'Eliminazione completata: {success_count} eliminate, {error_count} errori',
            'activities_found': activities_found,
            'deleted_count': success_count,
            'error_count': error_count,
            'deleted_ids': deleted_activities
        })
        
    except Exception as e:
        logging.error(f"ERRORE durante eliminazione ore: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore durante eliminazione: {str(e)}'
        })

@app.route('/delete-time-activities.html')
def delete_time_activities_page():
    """Serve la pagina per eliminare TimeActivity"""
    return render_template('delete-time-activities.html')

@app.route('/qb-tracker-stats', methods=['GET'])
def qb_tracker_stats():
    """Endpoint per ottenere statistiche complete del tracker QB"""
    try:
        operation_type = request.args.get('type', None)  # invoices, time_activities, general
        
        stats = qb_tracker.get_statistics(operation_type)
        
        # Statistiche aggiuntive
        additional_stats = {}
        if not operation_type or operation_type == 'time_activities':
            # Conta progetti unici con ore importate
            time_activities_dict = qb_tracker._load_status('time_activities')
            unique_projects = set()
            unique_employees = set()
            
            for key in time_activities_dict.keys():
                if ':' in key:
                    project_id, employee_name = key.split(':', 1)
                    unique_projects.add(project_id)
                    unique_employees.add(employee_name)
            
            additional_stats['time_activities_extra'] = {
                'unique_projects': len(unique_projects),
                'unique_employees': len(unique_employees)
            }
        elif operation_type == 'invoices':
            # Statistiche specifiche per le fatture
            invoice_stats = qb_tracker.get_invoice_statistics()
            additional_stats['invoice_details'] = invoice_stats.get('details', {})
        
        return jsonify({
            'success': True,
            'stats': stats,
            'additional_stats': additional_stats,
            'message': 'Statistiche recuperate con successo'
        })
        
    except Exception as e:
        logging.error(f"Errore recuperando statistiche tracker: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Errore nel recupero delle statistiche'
        })

@app.route('/qb-tracker-project/<int:project_id>', methods=['GET'])
def qb_tracker_project_summary(project_id):
    """Endpoint per ottenere il riassunto completo di un progetto"""
    try:
        summary = qb_tracker.get_project_summary(project_id)
        
        return jsonify({
            'success': True,
            'project_summary': summary,
            'message': f'Riassunto progetto {project_id} recuperato con successo'
        })
        
    except Exception as e:
        logging.error(f"Errore recuperando riassunto progetto {project_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Errore nel recupero del riassunto per progetto {project_id}'
        })

@app.route('/qb-tracker-export', methods=['POST'])
def qb_tracker_export():
    """Endpoint per esportare i dati del tracker in CSV"""
    try:
        data = request.get_json()
        operation_type = data.get('operation_type', 'time_activities')
        
        if operation_type not in ['invoices', 'time_activities', 'general']:
            return jsonify({
                'success': False,
                'error': 'Tipo operazione non valido. Usa: invoices, time_activities, general'
            })
        
        output_file = qb_tracker.export_to_csv(operation_type)
        
        return jsonify({
            'success': True,
            'output_file': output_file,
            'message': f'Dati {operation_type} esportati in {output_file}'
        })
        
    except Exception as e:
        logging.error(f"Errore durante export: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Errore durante esportazione'
        })

@app.route('/qb-tracker-cleanup', methods=['POST'])
def qb_tracker_cleanup():
    """Endpoint per pulire entry vecchie dal tracker"""
    try:
        data = request.get_json()
        operation_type = data.get('operation_type', 'time_activities')
        days_old = data.get('days_old', 30)
        
        if operation_type not in ['invoices', 'time_activities', 'general']:
            return jsonify({
                'success': False,
                'error': 'Tipo operazione non valido. Usa: invoices, time_activities, general'
            })
        
        removed_count = qb_tracker.cleanup_old_entries(operation_type, days_old)
        
        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Rimossi {removed_count} entry vecchi da {operation_type}'
        })
        
    except Exception as e:
        logging.error(f"Errore durante cleanup: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Errore durante pulizia'
        })

@app.route('/excel-import-stats', methods=['GET'])
def excel_import_stats():
    """Endpoint per visualizzare statistiche importazioni Excel"""
    import_type = request.args.get('type', 'hours')  # hours, invoices
    
    try:
        # Ottieni tutte le importazioni Excel
        all_imports = qb_tracker.get_all_excel_imports(import_type)
        
        if not all_imports:
            return jsonify({
                'success': True,
                'message': f'Nessuna importazione Excel trovata per tipo: {import_type}',
                'stats': {},
                'imports': []
            })
        
        # Calcola statistiche
        stats = {
            'total_imports': len(all_imports),
            'success': 0,
            'partial': 0,
            'error': 0,
            'recent_imports': []
        }
        
        import_list = []
        for key, data in all_imports.items():
            status = data.get('status', 'unknown')
            if status == 'success':
                stats['success'] += 1
            elif status == 'partial':
                stats['partial'] += 1
            elif status == 'error':
                stats['error'] += 1
            
            import_info = {
                'key': key,
                'status': status,
                'message': data.get('message', ''),
                'timestamp': data.get('timestamp', ''),
                'details': data.get('details', {})
            }
            import_list.append(import_info)
        
        # Ordina per timestamp (più recenti prima)
        import_list.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        stats['recent_imports'] = import_list[:10]  # Ultimi 10
        
        return jsonify({
            'success': True,
            'stats': stats,
            'imports': import_list,
            'total': len(import_list)
        })
        
    except Exception as e:
        logging.error(f"Errore recupero statistiche Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/excel-import-details/<import_key>', methods=['GET'])
def excel_import_details(import_key):
    """Endpoint per visualizzare dettagli di una specifica importazione Excel"""
    import_type = request.args.get('type', 'hours')
    
    try:
        import_data = qb_tracker.get_excel_import_status(import_type, import_key)
        
        if not import_data:
            return jsonify({
                'success': False,
                'error': 'Importazione non trovata'
            })
        
        return jsonify({
            'success': True,
            'import_key': import_key,
            'import_type': import_type,
            'data': import_data
        })
        
    except Exception as e:
        logging.error(f"Errore recupero dettagli importazione Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/excel-import-stats.html')
def excel_import_stats_page():
    """Serve la pagina per visualizzare statistiche importazioni Excel"""
    return render_template('excel-import-stats.html')

@app.route('/webhook-manager.html')
def webhook_manager_page():
    """Serve la pagina per gestire i webhook"""
    return render_template('webhook-manager.html')

def find_customer_by_project_name_web(access_token, project_name):
    """Trova il Customer ID per nome del progetto (versione per web)"""
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
                
                # Verifica se il nome del progetto è contenuto nel display name del customer
                if project_name.lower() in display_name.lower():
                    logging.info(f"Trovato Customer '{display_name}' per progetto '{project_name}' (ID: {customer['Id']})")
                    return customer["Id"], display_name
        
        logging.warning(f"Nessun Customer trovato per il progetto '{project_name}'")
        return None, None
        
    except Exception as e:
        logging.error(f"Errore ricerca customer per progetto: {e}")
        return None, None

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    """Endpoint per ricevere webhook da sistemi esterni"""
    logging.info("WEBHOOK RICEVUTO")
    
    try:
        # Ottieni dati della richiesta
        headers = dict(request.headers)
        data = request.get_json() if request.is_json else request.form.to_dict()
        
        # Se non c'è JSON, prova a parsare come form data o text
        if not data:
            if request.form:
                data = request.form.to_dict()
            else:
                data = {"raw_content": request.get_data(as_text=True)}
        
        # Determina la fonte del webhook (logica migliorata)
        source = "unknown"
        
        # 1. Controlla gli header HTTP
        if 'user-agent' in headers:
            user_agent = headers['user-agent'].lower()
            if 'rentman' in user_agent:
                source = "rentman"
            elif 'quickbooks' in user_agent:
                source = "quickbooks"
            elif 'zapier' in user_agent:
                source = "zapier"
            elif 'github' in user_agent:
                source = "github"
            elif 'gitlab' in user_agent:
                source = "gitlab"
        
        # 2. Controlla header specifici per identificare la fonte
        if headers.get('x-webhook-source'):
            source = headers['x-webhook-source']
        elif headers.get('x-rentman-signature') or headers.get('x-rentman-webhook'):
            source = "rentman"
        elif headers.get('x-github-event'):
            source = "github"
        elif headers.get('x-gitlab-event'):
            source = "gitlab"
        elif headers.get('x-zapier-source'):
            source = "zapier"
        
        # 3. Analizza il payload per identificare la fonte
        if source == "unknown" and data:
            payload_str = str(data).lower()
            if data.get('account') == 'itinerapro' or 'rentman' in payload_str:
                source = "rentman"
            elif data.get('zen_id') or 'zendesk' in payload_str:
                source = "zendesk"
            elif data.get('repository') and data.get('commits'):
                source = "github"
            elif 'quickbooks' in payload_str:
                source = "quickbooks"
        
        logging.info(f"Webhook da fonte: {source}")
        logging.info(f"Headers: {headers}")
        logging.info(f"Payload: {data}")
        
        # Salva nel database
        from db_config import save_webhook_to_db
        success, message = save_webhook_to_db(source, data, headers)
        
        if success:
            logging.info(f"Webhook salvato: {message}")
            
            # Estrai l'ID del webhook dal messaggio di risposta
            webhook_db_id = None
            if "ID: " in message:
                try:
                    webhook_db_id = int(message.split("ID: ")[1])
                    logging.info(f"🔍 DEBUG: Estratto webhook_db_id: {webhook_db_id}")
                except (ValueError, IndexError):
                    logging.warning(f"Impossibile estrarre webhook_db_id da: {message}")
            
            # Qui puoi aggiungere logica di elaborazione automatica
            # ad esempio, se è un webhook di progetto completato, elimina ore
            try:
                process_webhook_automatically(data, source, webhook_db_id)
            except Exception as e:
                logging.warning(f"Errore elaborazione automatica webhook: {e}")
            
            return jsonify({
                'success': True,
                'message': 'Webhook ricevuto e salvato',
                'source': source,
                'webhook_id': data.get('id', 'unknown'),
                'db_id': webhook_db_id
            }), 200
        else:
            logging.error(f"Errore salvataggio webhook: {message}")
            return jsonify({
                'success': False,
                'error': f'Errore salvataggio: {message}'
            }), 500
            
    except Exception as e:
        logging.error(f"Errore elaborazione webhook: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore elaborazione webhook: {str(e)}'
        }), 500

def process_webhook_automatically(data, source, webhook_db_id=None):
    """Elabora automaticamente i webhook ricevuti"""
    try:
        # Estrai informazioni dal payload
        event_type = data.get('event') or data.get('type') or data.get('event_type') or data.get('eventType')
        
        # Estrazione avanzata project_id per webhook Rentman reali
        project_id = data.get('project_id') or data.get('projectId') or (data.get('project', {}).get('id') if isinstance(data.get('project'), dict) else None)
        
        # Per SubProject, controlla se c'è un project_id nel data object
        data_object = data.get('data', {})
        if isinstance(data_object, dict) and data_object.get('project_id'):
            project_id = data_object.get('project_id')
        
        # Se non trovato, prova nell'array items (formato webhook Rentman reale)
        if not project_id and 'items' in data and isinstance(data['items'], list) and len(data['items']) > 0:
            first_item = data['items'][0]
            logging.info(f"🔍 DEBUG: Analizzando first_item: {first_item}")
            if isinstance(first_item, dict):
                # Per SubProject reali, prendi project_id dal parent.id
                if data.get('itemType', '').lower() == 'subproject':
                    logging.info(f"🔍 DEBUG: ItemType è SubProject, cercando parent.id")
                    # Webhook reale: parent.id contiene il project_id
                    parent = first_item.get('parent', {})
                    logging.info(f"🔍 DEBUG: Parent object: {parent}")
                    if isinstance(parent, dict):
                        project_id = parent.get('id')
                        logging.info(f"🔍 DEBUG: Project ID estratto da parent.id: {project_id}")
                    # Fallback: cerca project_id nell'item stesso  
                    if not project_id:
                        project_id = first_item.get('project_id')
                        logging.info(f"🔍 DEBUG: Project ID fallback da project_id: {project_id}")
                elif first_item.get('type', '').lower() in ['subproject', 'sub-project']:
                    # Webhook test format
                    project_id = first_item.get('project_id')
                    logging.info(f"🔍 DEBUG: Test format - project_id: {project_id}")
                else:
                    # Project normale
                    project_id = first_item.get('id')
                    logging.info(f"🔍 DEBUG: Project normale - id: {project_id}")
        
        # Estrazione item_type con normalizzazione case-insensitive - AGGIUNTO data.get('type')
        raw_item_type = data.get('itemType') or data.get('item_type') or data.get('type')
        item_type = None
        if raw_item_type:
            raw_lower = raw_item_type.lower()
            if raw_lower in ['project']:
                item_type = "Project"
            elif raw_lower in ['subproject', 'sub-project']:
                item_type = "SubProject"
            else:
                item_type = raw_item_type  # Mantieni originale per altri tipi
        
        logging.info(f"🔍 DEBUG estrazione avanzata (v2.0):")
        logging.info(f"   Raw project_id trovato: {project_id}")
        logging.info(f"   Raw item_type trovato: {raw_item_type}")
        if 'items' in data:
            logging.info(f"   Items array: {data['items']}")
        
        # Estrai informazioni utente
        user_info = None
        if 'user' in data:
            user_data = data['user']
            if isinstance(user_data, dict):
                user_name = user_data.get('name') or user_data.get('displayname') or user_data.get('username')
                user_info = f"{user_name} (ID: {user_data.get('id')})" if user_name else f"ID: {user_data.get('id')}"
            else:
                user_info = str(user_data)
        elif 'userId' in data:
            user_info = f"ID: {data['userId']}"
        elif 'username' in data:
            user_info = data['username']
        
        logging.info(f"🤖 ELABORAZIONE AUTOMATICA WEBHOOK:")
        logging.info(f"  Fonte: {source}")
        logging.info(f"  Evento: {event_type or 'N/A'}")
        logging.info(f"  Progetto: {project_id or 'N/A'}")
        logging.info(f"  ItemType: {item_type or 'N/A'}")
        logging.info(f"  Utente: {user_info or 'N/A'}")
        
        # 🎯 TRACKING AUTOMATICO CAMBI DI STATO PROGETTI E SUBPROGETTI
        if (source == "rentman" and 
            project_id and 
            event_type == "update" and 
            (item_type == "Project" or item_type == "SubProject")):
            
            logging.info(f"🔍 DEBUG: Condizioni tracking soddisfatte!")
            logging.info(f"   Source: {source}")
            logging.info(f"   Project ID: {project_id}")
            logging.info(f"   Event Type: {event_type}")
            logging.info(f"   Item Type: {item_type} (normalized: {item_type.lower() if item_type else 'N/A'})")
            
            # Estrai lo status attuale dal payload
            current_status = None
            if isinstance(data.get('project'), dict):
                current_status = data['project'].get('status')
                logging.info(f"   Status da data['project']: {current_status}")
            elif isinstance(data.get('subproject'), dict):
                current_status = data['subproject'].get('status')
                logging.info(f"   Status da data['subproject']: {current_status}")
            elif isinstance(data.get('data'), dict):
                current_status = data['data'].get('status')
                logging.info(f"   Status da data['data']: {current_status}")
            elif 'status' in data:
                current_status = data['status']
                logging.info(f"   Status da data['status']: {current_status}")
            
            # Se lo status non è nel webhook, recuperalo da Rentman API
            if not current_status:
                logging.info(f"   Status non trovato nel webhook, recupero da Rentman API...")
                if item_type == "SubProject":
                    # Per SubProject, usa l'ID del subproject stesso per recuperare lo status
                    subproject_id = None
                    if 'items' in data and isinstance(data['items'], list) and len(data['items']) > 0:
                        subproject_id = data['items'][0].get('id')
                    if subproject_id:
                        current_status = get_item_status_from_rentman(subproject_id, "subproject")
                elif item_type == "Project":
                    # Per Project, usa il project_id
                    current_status = get_item_status_from_rentman(project_id, "project")
                
                if current_status:
                    logging.info(f"   Status recuperato da API: {current_status}")
                else:
                    logging.warning(f"   Impossibile recuperare status da API")
            
            # DEBUG: Mostra tutto il payload per capire la struttura
            logging.info(f"🔍 DEBUG PAYLOAD COMPLETO: {data}")
            
            if current_status:
                item_label = "SUBPROGETTO" if item_type == "SubProject" else "PROGETTO"
                logging.info(f"📊 RILEVATO AGGIORNAMENTO {item_label} {project_id}")
                logging.info(f"   ItemType: {item_type}")
                logging.info(f"   Status attuale: {current_status}")
                
                logging.info(f"🔍 DEBUG: Chiamando track_project_status_change...")
                logging.info(f"   project_id: {project_id} (tipo: {type(project_id)})")
                logging.info(f"   current_status: {current_status}")
                logging.info(f"   webhook_db_id: {webhook_db_id}")
                logging.info(f"   item_type: {item_type}")
                
                # Traccia il cambio di stato e triggera automazioni
                from db_config import track_project_status_change
                
                try:
                    status_changed = track_project_status_change(
                        project_id=int(project_id),
                        current_status=current_status,
                        webhook_id=webhook_db_id,
                        item_type=item_type  # Passa il tipo per il logging
                    )
                    
                    logging.info(f"🔍 DEBUG: track_project_status_change completata. Risultato: {status_changed}")
                    
                    if status_changed:
                        logging.info(f"🔔 CAMBIO DI STATO PROCESSATO CON AUTOMAZIONI - {item_label} {project_id}")
                    else:
                        logging.info(f"📝 Status {item_label.lower()} {project_id} confermato (nessun cambio)")
                        
                except Exception as e:
                    logging.error(f"❌ ERRORE in track_project_status_change: {e}")
                    import traceback
                    logging.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            else:
                logging.warning(f"⚠️  Webhook {item_type} {project_id} senza campo status")
                logging.warning(f"⚠️  Campi disponibili nel payload: {list(data.keys())}")
        else:
            logging.info(f"🔍 DEBUG: Condizioni tracking NON soddisfatte:")
            logging.info(f"   Source è rentman: {source == 'rentman'}")
            logging.info(f"   Project ID presente: {bool(project_id)}")
            logging.info(f"   Event type è update: {event_type == 'update'}")
            logging.info(f"   Item type è Project/SubProject: {item_type in ['Project', 'SubProject']}")
            logging.info(f"   Raw item_type ricevuto: {raw_item_type}")
            logging.info(f"   Item type normalizzato: {item_type}")
        
        # 🎯 ALTRI AUTOMATISMI LEGACY (manteniamo per compatibilità)
        if source == "rentman" and event_type in ["project.completed", "project.cancelled"]:
            if project_id:
                logging.info(f"🔄 Elaborazione legacy: Progetto {project_id} {event_type} da utente {user_info or 'N/A'}")
                # Qui potresti mantenere logiche legacy se necessario
        
        # Altre logiche di elaborazione automatica...
        
    except Exception as e:
        logging.error(f"❌ Errore elaborazione automatica webhook: {e}")
        import traceback
        logging.error(f"❌ TRACEBACK: {traceback.format_exc()}")

@app.route('/webhooks', methods=['GET'])
def list_webhooks():
    """Endpoint per visualizzare i webhook ricevuti"""
    try:
        # Parametri di filtro
        source = request.args.get('source')
        event_type = request.args.get('event_type')
        project_id = request.args.get('project_id')
        processed = request.args.get('processed')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Paginazione
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
        except (ValueError, TypeError):
            page = 1
            per_page = 50
        
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 50
        
        offset = (page - 1) * per_page
        
        # Costruisci filtri
        filters = {}
        if source:
            filters['source'] = source
        if event_type:
            filters['event_type'] = event_type
        if project_id:
            filters['project_id'] = project_id
        if processed is not None:
            filters['processed'] = processed.lower() in ['true', '1', 'yes']
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Recupera webhook dal database
        from db_config import get_webhooks_from_db
        webhooks, total_count = get_webhooks_from_db(filters, per_page, offset)
        
        if webhooks is not None:
            total_pages = (total_count + per_page - 1) // per_page
            
            return jsonify({
                'success': True,
                'webhooks': webhooks,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': total_pages
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': total_count  # In caso di errore, total_count contiene il messaggio
            }), 500
            
    except Exception as e:
        logging.error(f"Errore recupero webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/webhooks/<webhook_id>/process', methods=['POST'])
def process_webhook_manual(webhook_id):
    """Endpoint per elaborare manualmente un webhook"""
    try:
        # Recupera il webhook dal database
        from db_config import get_webhooks_from_db
        webhooks, _ = get_webhooks_from_db({'webhook_id': webhook_id}, 1, 0)
        
        if not webhooks:
            return jsonify({
                'success': False,
                'error': 'Webhook non trovato'
            }), 404
        
        webhook = webhooks[0]
        
        # Elabora il webhook
        try:
            import json
            payload = json.loads(webhook['payload']) if isinstance(webhook['payload'], str) else webhook['payload']
            
            # Estrai informazioni utili dal payload
            extracted_data = {
                'source': webhook.get('source', 'unknown'),
                'event_type': None,
                'project_id': None,
                'user_info': None,
                'timestamp': webhook.get('received_at', 'N/A')
            }
            
            # Estrai tipo di evento (cerca in vari campi possibili)
            event_type = (payload.get('event') or 
                         payload.get('type') or 
                         payload.get('event_type') or 
                         payload.get('eventType'))
            extracted_data['event_type'] = event_type
            
            # Estrai ID progetto (cerca in vari campi possibili)
            project_id = (payload.get('project_id') or 
                         payload.get('projectId') or 
                         payload.get('project', {}).get('id') if isinstance(payload.get('project'), dict) else None)
            extracted_data['project_id'] = project_id
            
            # Estrai informazioni utente (cerca in vari campi possibili)
            user_info = None
            if 'user' in payload:
                user_data = payload['user']
                if isinstance(user_data, dict):
                    user_info = {
                        'id': user_data.get('id'),
                        'name': user_data.get('name') or user_data.get('displayname') or user_data.get('username'),
                        'email': user_data.get('email'),
                        'ref': user_data.get('ref')
                    }
                else:
                    user_info = {'raw': user_data}
            elif 'userId' in payload:
                user_info = {'id': payload['userId']}
            elif 'username' in payload:
                user_info = {'name': payload['username']}
            
            extracted_data['user_info'] = user_info
            
            # Crea messaggio dettagliato con le informazioni estratte
            details = []
            details.append(f"Fonte: {extracted_data['source']}")
            if extracted_data['event_type']:
                details.append(f"Evento: {extracted_data['event_type']}")
            if extracted_data['project_id']:
                details.append(f"Progetto: {extracted_data['project_id']}")
            if extracted_data['user_info']:
                if isinstance(extracted_data['user_info'], dict):
                    user_parts = []
                    if extracted_data['user_info'].get('name'):
                        user_parts.append(f"Nome: {extracted_data['user_info']['name']}")
                    if extracted_data['user_info'].get('id'):
                        user_parts.append(f"ID: {extracted_data['user_info']['id']}")
                    if extracted_data['user_info'].get('email'):
                        user_parts.append(f"Email: {extracted_data['user_info']['email']}")
                    if user_parts:
                        details.append(f"Utente: {', '.join(user_parts)}")
                    elif extracted_data['user_info'].get('raw'):
                        details.append(f"Utente: {extracted_data['user_info']['raw']}")
            
            detailed_message = f"Webhook {webhook_id} elaborato manualmente - " + " | ".join(details)
            
            # Log dettagliato
            logging.info(f"ELABORAZIONE MANUALE WEBHOOK {webhook_id}:")
            logging.info(f"  Fonte: {extracted_data['source']}")
            logging.info(f"  Evento: {extracted_data['event_type'] or 'N/A'}")
            logging.info(f"  Progetto: {extracted_data['project_id'] or 'N/A'}")
            logging.info(f"  Utente: {extracted_data['user_info'] or 'N/A'}")
            logging.info(f"  Timestamp: {extracted_data['timestamp']}")
            
            # Aggiorna lo stato nel database
            from db_config import update_webhook_processing_status
            update_webhook_processing_status(webhook_id, True, detailed_message, None)
            
            return jsonify({
                'success': True,
                'message': detailed_message,
                'webhook': webhook,
                'extracted_data': extracted_data
            })
            
        except Exception as e:
            error_msg = f"Errore elaborazione: {str(e)}"
            from db_config import update_webhook_processing_status
            update_webhook_processing_status(webhook_id, True, None, error_msg)
            
            return jsonify({
                'success': False,
                'error': error_msg
            }), 500
            
    except Exception as e:
        logging.error(f"Errore elaborazione manuale webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/project-status-dashboard')
def project_status_dashboard():
    """Dashboard per visualizzare i cambi di stato dei progetti"""
    return render_template('project-status-dashboard.html')

@app.route('/api/project-status-changes')
def api_project_status_changes():
    """API per recuperare i cambi di stato dei progetti"""
    try:
        # Parametri di filtro
        project_id = request.args.get('project_id')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        automation_status = request.args.get('automation_status')  # 'triggered', 'not_triggered', 'all'
        
        # Paginazione
        try:
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
        except (ValueError, TypeError):
            page = 1
            per_page = 50
        
        offset = (page - 1) * per_page
        
        from db_config import get_db_connection
        connection = get_db_connection(use_database=True)
        if not connection:
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Costruisci query con filtri
            base_query = """
            SELECT 
                id, project_id, old_status, new_status, old_status_name, new_status_name,
                changed_at, automation_triggered, automation_result, automation_error,
                detected_via, webhook_id
            FROM project_status_tracking
            WHERE 1=1
            """
            
            params = []
            conditions = []
            
            if project_id:
                conditions.append("project_id = %s")
                params.append(int(project_id))
            
            if date_from:
                conditions.append("changed_at >= %s")
                params.append(date_from)
            
            if date_to:
                conditions.append("changed_at <= %s")
                params.append(date_to + " 23:59:59")  # Include tutto il giorno
            
            if automation_status == 'triggered':
                conditions.append("automation_triggered = 1")
            elif automation_status == 'not_triggered':
                conditions.append("automation_triggered = 0")
            
            if conditions:
                base_query += " AND " + " AND ".join(conditions)
            
            # Query per conteggio totale
            count_query = "SELECT COUNT(*) as total FROM project_status_tracking WHERE 1=1"
            if conditions:
                count_query += " AND " + " AND ".join(conditions)
            
            cursor.execute(count_query, params)
            total_count = cursor.fetchone()['total']
            
            # Query principale con paginazione
            final_query = base_query + " ORDER BY changed_at DESC LIMIT %s OFFSET %s"
            final_params = params + [per_page, offset]
            
            cursor.execute(final_query, final_params)
            changes = cursor.fetchall()
            
            # Calcola statistiche
            stats_query = """
            SELECT 
                COUNT(*) as total_changes,
                SUM(CASE WHEN automation_triggered = 1 THEN 1 ELSE 0 END) as automated_changes,
                COUNT(DISTINCT project_id) as unique_projects
            FROM project_status_tracking
            """
            if conditions:
                stats_query += " WHERE " + " AND ".join(conditions)
            
            cursor.execute(stats_query, params)
            stats = cursor.fetchone()
            
            total_pages = (total_count + per_page - 1) // per_page
            
            return jsonify({
                'success': True,
                'changes': changes,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'total_pages': total_pages
                },
                'stats': stats
            })
            
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    except Exception as e:
        logging.error(f"Errore API cambi stato: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def get_item_status_from_rentman(item_id, item_type):
    """Recupera lo status di un item (Project/SubProject) da Rentman API"""
    try:
        import requests
        import config
        
        # Determina l'endpoint API corretto  
        if item_type.lower() == 'project':
            endpoint = f"projects/{item_id}"
        elif item_type.lower() == 'subproject':
            endpoint = f"subprojects/{item_id}"
        else:
            logging.warning(f"Tipo item non supportato per recupero status: {item_type}")
            return None
        
        # Costruisce l'URL completo
        url = f"{config.REN_BASE_URL}/{endpoint}"
        
        # Headers per autenticazione Rentman
        headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        
        logging.info(f"🔍 DEBUG: Chiamata API Rentman - URL: {url}")
        
        # Chiama l'API di Rentman
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                status = data['data'].get('status')
                logging.info(f"✅ Status recuperato da Rentman API per {item_type} {item_id}: {status}")
                return status
            else:
                logging.warning(f"⚠️ Nessun campo 'data' nella risposta API per {item_type} {item_id}")
                return None
        else:
            logging.error(f"❌ Errore API Rentman: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Errore recupero status da Rentman API per {item_type} {item_id}: {e}")
        return None

if __name__ == '__main__':
    print("🚀 Avvio Rentman Project Manager...")
    print("🔗 Import diretti:", 
          "✅ Fatture" if INVOICE_IMPORT_SUCCESS else "❌ Fatture (subprocess)", 
          "✅ Ore" if HOURS_IMPORT_SUCCESS else "❌ Ore (subprocess)")
    
    # Inizializza il database MySQL
    print("🗄️ Inizializzazione database MySQL...")
    try:
        connection_ok, connection_msg = test_connection()
        if connection_ok:
            print(f"✅ {connection_msg}")
            if create_tables():
                print("✅ Tabelle database create/verificate con successo")
            else:
                print("⚠️ Errore nella creazione delle tabelle database")
        else:
            print(f"⚠️ Problemi con il database: {connection_msg}")
            print("⚠️ La funzionalità di salvataggio database sarà disabilitata")
    except Exception as e:
        print(f"⚠️ Errore inizializzazione database: {e}")
        print("⚠️ La funzionalità di salvataggio database sarà disabilitata")
    
    # Porta configurabile via env/config, default 5001
    app_port = int(os.getenv("APP_PORT", getattr(config, "APP_PORT", 5001)))
    app.run(host="0.0.0.0", port=app_port, debug=True)
