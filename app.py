from flask import Flask, request, jsonify, send_from_directory, render_template
from rentman_api import list_projects_by_date, get_project_and_customer
from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
from create_or_update_invoice_for_project import create_or_update_invoice_for_project
from qb_time_activity import import_ore_da_excel, inserisci_ore
import threading
import time
import subprocess
import sys
import os
import tempfile
from flask import request
import csv
import io

# Importiamo direttamente dal file
import create_or_update_invoice_for_project
 

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
    from token_manager import TokenManager
    
    try:
        tm = TokenManager()
        tm.load_refresh_token()
        token = tm.get_access_token()
        
        is_valid = token != "invalid_token_handled_gracefully"
        
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

@app.route('/lista-progetti', methods=['POST'])
def lista_progetti():
    data = request.json
    try:
        print("[INFO] Richiesta lista progetti ricevuta")
        progetti = list_projects_by_date(data.get('fromDate'), data.get('toDate'))
        print(f"[INFO] Progetti restituiti all'utente: {len(progetti)}")
        # Escludi sempre i progetti con status 'IN OPZIONE' (case insensitive)
        progetti = [p for p in progetti if (p.get('status') or '').strip().upper() != 'IN OPZIONE']
        print(f"[INFO] Progetti dopo esclusione 'IN OPZIONE': {len(progetti)}")
        output = [{
            'id': p.get('id'),
            'number': p.get('number'),
            'name': p.get('name'),
            'status': p.get('status'),
            'equipment_period_from': p.get('equipment_period_from'),
            'equipment_period_to': p.get('equipment_period_to'),
            'project_type_name': p.get('project_type_name'),
            'project_value': p.get('project_value'),
            'manager_name': p.get('manager_name'),
            'manager_email': p.get('manager_email')
        } for p in progetti]
        return jsonify({'projects': output})
    except Exception as e:
        print(f"[ERRORE] {e}")
        return jsonify({'error': str(e)}), 200

@app.route('/elabora-selezionati', methods=['POST'])
def elabora_selezionati():
    """Elabora fatturazione per progetti selezionati (SENZA ore)"""
    data = request.json
    selected_projects = data.get('selectedProjects', [])
    
    if not selected_projects:
        return jsonify({'error': 'Nessun progetto selezionato'}), 400
    
    print(f"💰 ELABORAZIONE FATTURE per {len(selected_projects)} progetti")
    
    # Lista per tenere traccia dei risultati
    results = []
    
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
                    if is_simulated:
                        print(f"✅ Fattura progetto {project_id} completata (SIMULAZIONE - token non valido)")
                        return {
                            'project_id': project_id,
                            'project_name': project_name,
                            'status': 'success_simulated',
                            'output': str(result),
                            'error': None,
                            'details': result,
                            'message': "Operazione simulata: token QuickBooks non valido"
                        }
                    else:
                        print(f"✅ Fattura progetto {project_id} completata")
                        return {
                            'project_id': project_id,
                            'project_name': project_name,
                            'status': 'success',
                            'output': str(result),
                            'error': None,
                            'details': result
                        }
                else:
                    print(f"❌ Fattura progetto {project_id} fallita: {result.get('error')}")
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
                    timeout=300  # 5 minuti timeout
                )
                
                if result.returncode == 0:
                    print(f"✅ Fattura progetto {project_id} completata")
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'success',
                        'output': result.stdout,
                        'error': None
                    }
                else:
                    print(f"❌ Fattura progetto {project_id} fallita")
                    return {
                        'project_id': project_id,
                        'project_name': project_name,
                        'status': 'error',
                        'output': result.stdout,
                        'error': result.stderr
                    }
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Fattura progetto {project_id} timeout")
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': 'timeout',
                'output': '',
                'error': 'Timeout dopo 5 minuti'
            }
        except Exception as e:
            print(f"💥 Errore fattura progetto {project_id}: {e}")
            return {
                'project_id': project_id,
                'project_name': project_name,
                'status': 'error',
                'output': '',
                'error': str(e)
            }
    
    # Elaborazione sequenziale
    for project in selected_projects:
        project_id = project.get('id')
        project_name = project.get('name', 'Nome sconosciuto')
        
        result = elabora_fattura_progetto(project_id, project_name)
        results.append(result)
        
        # Piccola pausa tra un progetto e l'altro
        time.sleep(1)
    
    # Statistiche finali
    success_count = len([r for r in results if r['status'] == 'success'])
    simulated_count = len([r for r in results if r['status'] == 'success_simulated'])
    error_count = len([r for r in results if r['status'] == 'error'])
    timeout_count = len([r for r in results if r['status'] == 'timeout'])
    
    print(f"💰 ELABORAZIONE FATTURE COMPLETATA:")
    print(f"   ✅ Successi: {success_count}")
    if simulated_count > 0:
        print(f"   🔄 Simulati: {simulated_count} (token QuickBooks non valido)")
    print(f"   ❌ Errori: {error_count}")
    print(f"   ⏰ Timeout: {timeout_count}")
    
    message = f'Elaborazione fatture completata: {success_count} successi'
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
    data_attivita = request.form.get('data_attivivita')
    if not data_attivita:
        return jsonify({'success': False, 'error': 'Data attività mancante'}), 400
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nessun file selezionato'}), 400
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            file.save(tmp.name)
            tmp_filepath = tmp.name
        report = import_ore_da_excel(tmp_filepath, data_attivita)
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

@app.route('/upload-to-qb', methods=['POST'])
def upload_to_qb():
    """Riceve dati CSV dal frontend, li importa su QuickBooks come fatture di acquisto (Bills)"""
    try:
        data = request.get_json()
        csv_data = data.get('csv')
        if not csv_data:
            return jsonify({'success': False, 'error': 'Nessun dato CSV ricevuto'}), 400

        # Import funzione per ricerca TaxCodeId
        from get_quickbooks_taxcodes import get_quickbooks_taxcode_id_by_percent

        # Parsing CSV in memoria
        f = io.StringIO(csv_data)
        reader = csv.DictReader(f)
        bills = []
        for row in reader:
            # Estrai percentuale IVA dalla colonna LineTaxCode (es. "22%")
            line_tax_code = row.get('LineTaxCode', '')
            percent = None
            if line_tax_code:
                import re
                m = re.search(r'(\d+)', line_tax_code)
                if m:
                    percent = m.group(1)
            taxcode_id = None
            if percent:
                taxcode_id = get_quickbooks_taxcode_id_by_percent(percent)
            # Mappa i campi CSV ai dati richiesti da QuickBooksBillImporter
            bill = {
                'vendor_id': row.get('Supplier', '1'),
                'txn_date': row.get('BillDate', ''),
                'due_date': row.get('DueDate', ''),
                'ref_number': row.get('BillNo', ''),
                'memo': row.get('Memo', ''),
                'taxcode_id': taxcode_id,
                'line_items': [{
                    'amount': float(row.get('LineAmount', '0') or 0),
                    'description': row.get('LineDescription', ''),
                    'account_id': '1',
                    'taxcode_id': taxcode_id  # Passa anche a livello di riga
                }]
            }
            bills.append(bill)

        # Importa le fatture in batch (usa la classe QuickBooksBillImporter)
        from quickbooks_bill_importer import QuickBooksBillImporter  # Adatta il nome file se necessario
        from config import API_BASE_URL, REALM_ID
        from token_manager import TokenManager
        tm = TokenManager()
        access_token = tm.get_access_token()
        importer = QuickBooksBillImporter(API_BASE_URL, REALM_ID, access_token)
        # Trova o crea il fornitore per ogni bill
        for bill in bills:
            supplier_name = bill.get('vendor_id')
            if supplier_name:
                vendor_id = importer.find_or_create_vendor(supplier_name)
                if vendor_id:
                    bill['vendor_id'] = vendor_id
                else:
                    return jsonify({'success': False, 'error': f'Impossibile trovare o creare il fornitore: {supplier_name}'})
        result = importer.batch_import_bills(bills)
        # Se ci sono errori, restituisci success False e dettaglio errori
        if result['error_count'] > 0:
            return jsonify({'success': False, 'result': result, 'error': result['errors']})
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🚀 Avvio Rentman Project Manager...")
    print("🔗 Import diretti:", 
          "✅ Fatture" if INVOICE_IMPORT_SUCCESS else "❌ Fatture (subprocess)", 
          "✅ Ore" if HOURS_IMPORT_SUCCESS else "❌ Ore (subprocess)")
    app.run(host="0.0.0.0", port=5000, debug=True)