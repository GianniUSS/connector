import requests
import json

def test_api():
    """Invia una richiesta all'API Flask locale per verificare il progetto 3488"""
    url = "http://127.0.0.1:5000/lista-progetti"
    
    # Dati per la richiesta POST
    data = {
        "fromDate": "2025-01-01",
        "toDate": "2025-12-31"
    }
    
    print(f"🔍 Invio richiesta a {url} con date: {data['fromDate']} - {data['toDate']}")
    
    try:
        response = requests.post(url, json=data)
        if response.status_code != 200:
            print(f"❌ Errore API: Status code {response.status_code}")
            print(response.text)
            return
            
        result = response.json()
        
        # Controlla quanti progetti sono stati restituiti
        projects = result.get('projects', [])
        print(f"✅ Ricevuti {len(projects)} progetti")
        
        # Cerca il progetto 3488
        project_3488 = None
        for p in projects:
            if str(p.get('id')) == '3488':
                project_3488 = p
                break
                
        if project_3488:
            print(f"\n🎯 PROGETTO 3488 TROVATO:")
            print(f"ID: {project_3488.get('id')}")
            print(f"Nome: {project_3488.get('name')}")
            print(f"Numero: {project_3488.get('number')}")
            print(f"Stato: {project_3488.get('status')}")
            print(f"Tipo: {project_3488.get('project_type_name')}")
            print(f"Valore: {project_3488.get('project_value')}")
            
            # Analizza il tipo di valore
            value = project_3488.get('project_value')
            print(f"\nTipo valore: {type(value).__name__}")
            
            # Simula la visualizzazione nell'interfaccia
            html_value = f"€ {value}" if value else 'N/A'
            print(f"Visualizzazione HTML: {html_value}")
        else:
            print(f"⚠️ Progetto 3488 non trovato")
            
            # Mostra i primi progetti come riferimento
            print("\nPrimi 3 progetti ricevuti:")
            for i, p in enumerate(projects[:3]):
                print(f"Progetto {i+1}:")
                print(f"  ID: {p.get('id')}")
                print(f"  Nome: {p.get('name')}")
                print(f"  Valore: {p.get('project_value')}")
                
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_api()
