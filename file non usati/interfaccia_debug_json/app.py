from flask import Flask, request, jsonify, send_from_directory
import subprocess
from rentman_api import list_projects_by_date

app = Flask(__name__)

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/avvia-importazione', methods=['POST'])
def avvia():
    data = request.json
    result = subprocess.run(
        ['python', r'E:\ItineraWebHook\main_with_hours.py', data.get('projectId'), data.get('fromDate'), data.get('toDate')],
        capture_output=True, text=True
    )
    return jsonify({
        'message': 'Esecuzione completata.',
        'output': result.stdout + '\n' + result.stderr
    })

@app.route('/lista-progetti', methods=['POST'])
def lista_progetti():
    data = request.json
    try:
        # recupera e filtra
        progetti = list_projects_by_date(data.get('fromDate'), data.get('toDate'))
        output = [{'id': p.get('id'), 'name': p.get('name'), 'status': p.get('status')} for p in progetti]
        return jsonify({'projects': output})
    except Exception as e:
        return jsonify({'error': str(e)}), 200

if __name__ == '__main__':
    app.run(debug=True)