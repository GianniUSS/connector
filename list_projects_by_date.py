# Esempio di server Flask con debug completo
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import config
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Per permettere richieste dal browser

# Le tue funzioni API (usa la versione ottimizzata che ti ho dato)
from your_rentman_api import list_projects_by_date  # Importa la tua funzione

@app.route('/')
def home():
    return render_template('index.html')  # Il tuo file HTML

@app.route('/lista-progetti', methods=['POST'])
def lista_progetti():
    print("\n" + "="*50)
    print("🚀 ENDPOINT /lista-progetti chiamato")
    
    try:
        # Ricevi dati dal browser
        data = request.get_json()
        print(f"📥 Dati ricevuti dal browser: {data}")
        
        from_date = data.get('fromDate')
        to_date = data.get('toDate')
        print(f"📅 Date estratte: {from_date} → {to_date}")
        
        # Chiama la tua funzione API
        print("🔄 Chiamata list_projects_by_date...")
        projects = list_projects_by_date(from_date, to_date)
        print(f"📊 Progetti ricevuti dalla funzione: {len(projects) if projects else 0}")
        
        # 🔍 DEBUG CRITICO: Cosa stiamo per inviare?
        if projects:
            print("\n📤 DEBUG INVIO AL BROWSER - Primi 3 progetti:")
            for i, p in enumerate(projects[:3]):
                print(f"  🔍 Server Progetto {i+1}:")
                print(f"    📋 Dizionario completo: {p}")
                print(f"    🆔 ID: {repr(p.get('id'))} (tipo: {type(p.get('id'))})")
                print(f"    🔢 NUMBER: {repr(p.get('number'))} (tipo: {type(p.get('number'))})")
                print(f"    📝 NAME: {repr(p.get('name'))} (tipo: {type(p.get('name'))})")
                print(f"    📊 STATUS: {repr(p.get('status'))} (tipo: {type(p.get('status'))})")
                
                # Controllo chiavi del dizionario
                print(f"    🔑 Chiavi disponibili: {list(p.keys())}")
                
                # Test specifico per il number
                if 'number' in p:
                    print(f"    ✅ Campo 'number' PRESENTE: {repr(p['number'])}")
                else:
                    print(f"    ❌ Campo 'number' MANCANTE!")
                    
        else:
            print("⚠️ Lista progetti vuota o None")
        
        # Prepara risposta
        response_data = {"projects": projects or []}
        print(f"\n📤 Risposta finale da inviare:")
        print(f"   Tipo: {type(response_data)}")
        print(f"   Contenuto: {response_data}")
        
        # Controlla la serializzazione JSON
        import json
        try:
            json_test = json.dumps(response_data)
            print(f"✅ Serializzazione JSON OK (lunghezza: {len(json_test)})")
        except Exception as e:
            print(f"❌ ERRORE serializzazione JSON: {e}")
            return jsonify({"error": f"Errore serializzazione: {str(e)}"}), 500
        
        print("📡 Invio risposta al browser...")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"💥 ERRORE nell'endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/avvia-importazione', methods=['POST'])
def avvia_importazione():
    print("\n🔄 ENDPOINT /avvia-importazione chiamato")
    
    try:
        data = request.get_json()
        print(f"📥 Dati ricevuti: {data}")
        
        from_date = data.get('fromDate')
        to_date = data.get('toDate')
        
        # Qui aggiungi la tua logica di importazione
        # Per ora ritorna un messaggio di successo
        
        response = {
            "message": f"Importazione completata per periodo {from_date} - {to_date}",
            "success": True
        }
        
        print(f"📤 Risposta importazione: {response}")
        return jsonify(response)
        
    except Exception as e:
        print(f"💥 ERRORE importazione: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Avvio server Flask con debug completo...")
    print("📡 Server disponibile su: http://127.0.0.1:5000")
    print("🔍 Debug attivo - controlla i log per dettagli")
    app.run(debug=True, host='127.0.0.1', port=5000)