import requests
import json
import sys

def get_project_and_customer(projectId, apiToken, baseUrl):
    headers = {
        'Authorization': f'Bearer {apiToken}',
        'Accept': 'application/json'
    }
    print(f"Effettuando richiesta API a {baseUrl}/projects/{projectId}...")
    proj_url = f"{baseUrl}/projects/{projectId}"
    proj_res = requests.get(proj_url, headers=headers)
    if not proj_res.ok:
        raise Exception(f"Rentman API Error {proj_res.status_code}: {proj_res.text}")
    
    print(f"Risposta ricevuta, status code: {proj_res.status_code}")
    proj_payload = proj_res.json()
    project = proj_payload.get('data')
    
    cust_path = project.get('customer')
    if not cust_path:
        raise Exception(f"Nessun customer associato al progetto {projectId}")
    
    print(f"Recupero customer da {baseUrl}{cust_path}...")
    cust_url = f"{baseUrl}{cust_path}"
    cust_res = requests.get(cust_url, headers=headers)
    if not cust_res.ok:
        raise Exception(f"Rentman API Error {cust_res.status_code}: {cust_res.text}")
    
    cust_payload = cust_res.json()
    customer = cust_payload.get('data')
    return {'project': project, 'customer': customer}

if __name__ == '__main__':
    projectId = '3488'        # Progetto specifico da controllare
    apiToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'
    baseUrl = 'https://api.rentman.net'
    
    try:
        print(f"🔍 Recupero dati per il progetto {projectId}...")
        result = get_project_and_customer(projectId, apiToken, baseUrl)
        
        print("\n✅ RISULTATO COMPLETO:")
        # Estrai solo i campi essenziali per non avere output troppo lungo
        project = result.get('project', {})
        
        print("\n📝 INFORMAZIONI PRINCIPALI:")
        print(f"  - ID: {project.get('id')}")
        print(f"  - Nome: {project.get('name')}")
        print(f"  - Numero: {project.get('number')}")
        print(f"  - Tipo progetto: {project.get('project_type')}")
        
        print("\n💰 CAMPI RELATIVI AL VALORE:")
        for key, value in project.items():
            if any(term in key.lower() for term in ['price', 'cost', 'total', 'value', 'amount', 'budget']):
                print(f"  - {key}: {value}")
        
        print("\n🔍 CONTROLLO SPECIFICO CAMPI VALORE:")
        fields_to_check = [
            'price',
            'project_total_price',
            'project_total_price_cancelled',
            'project_rental_price',
            'project_sale_price',
            'project_crew_price',
            'project_transport_price',
            'project_other_price',
            'project_insurance_price'
        ]
        
        for field in fields_to_check:
            value = project.get(field)
            print(f"  - Campo '{field}': {value} (tipo: {type(value).__name__})")
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
        import traceback
        traceback.print_exc()
