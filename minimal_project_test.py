import requests

def get_project(project_id):
    """Recupera e stampa solo i dati essenziali di un progetto"""
    API_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'
    BASE_URL = 'https://api.rentman.net'
    
    headers = {
        'Authorization': f'Bearer {API_TOKEN}',
        'Accept': 'application/json'
    }
    
    url = f"{BASE_URL}/projects/{project_id}"
    print(f"Chiamata API: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Errore: Status code {response.status_code}")
            return
            
        data = response.json().get('data', {})
        
        print(f"\nDati progetto {project_id}:")
        print(f"ID: {data.get('id')}")
        print(f"Nome: {data.get('name')}")
        print(f"Numero: {data.get('number')}")
        
        print("\nCampi valore:")
        print(f"project_total_price: {data.get('project_total_price')}")
        print(f"project_total_price_cancelled: {data.get('project_total_price_cancelled')}")
        print(f"project_rental_price: {data.get('project_rental_price')}")
        print(f"project_sale_price: {data.get('project_sale_price')}")
        
    except Exception as e:
        print(f"Errore: {e}")

# Test con due progetti, uno è il 3488 in questione, l'altro è per confronto
print("=== TEST PROGETTO 3488 ===")
get_project('3488')

print("\n=== TEST PROGETTO 3441 (PER CONFRONTO) ===")
get_project('3441')
