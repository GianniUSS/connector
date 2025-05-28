from flask import Flask, request, jsonify, send_from_directory

import threading
import time
import subprocess
import sys
import os
from rentman_api import list_projects_by_date
from qb_customer import trova_o_crea_customer, trova_o_crea_subcustomer
from mapping import map_rentman_to_qbo_customer, map_rentman_to_qbo_subcustomer
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

if __name__ == '__main__':
    print("🚀 Avvio Rentman Project Manager...")
    print("🔗 Import diretti:", 
          "✅ Fatture" if INVOICE_IMPORT_SUCCESS else "❌ Fatture (subprocess)", 
          "✅ Ore" if HOURS_IMPORT_SUCCESS else "❌ Ore (subprocess)")
    app.run(host="0.0.0.0", port=5000, debug=True)