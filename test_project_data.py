import requests
import json

def get_project_and_customer(projectId, apiToken, baseUrl):
    headers = {
        'Authorization': f'Bearer {apiToken}',
        'Accept': 'application/json'
    }
    proj_url = f"{baseUrl}/projects/{projectId}"
    proj_res = requests.get(proj_url, headers=headers)
    if not proj_res.ok:
        raise Exception(f"Rentman API Error {proj_res.status_code}: {proj_res.text}")
    proj_payload = proj_res.json()
    project = proj_payload.get('data')
    cust_path = project.get('customer')
    if not cust_path:
        raise Exception(f"Nessun customer associato al progetto {projectId}")
    cust_url = f"{baseUrl}{cust_path}"
    cust_res = requests.get(cust_url, headers=headers)
    if not cust_res.ok:
        raise Exception(f"Rentman API Error {cust_res.status_code}: {cust_res.text}")
    cust_payload = cust_res.json()
    customer = cust_payload.get('data')
    return {'project': project, 'customer': customer}

if __name__ == '__main__':
    projectId = '3441'        # <-- il tuo projectId
    apiToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'          # <-- il tuo apiToken
    baseUrl = 'https://api.rentman.net'
    
    try:
        print(f"🔍 Recupero dati per il progetto {projectId}...")
        result = get_project_and_customer(projectId, apiToken, baseUrl)
        
        # Stampa l'intero risultato
        print("\n✅ RISULTATO COMPLETO:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Estrai il progetto per analisi
        project = result.get('project', {})
        
        # Stampa solo i campi relativi al valore
        print("\n💰 CAMPI RELATIVI AL VALORE:")
        value_fields_found = False
        for key, value in project.items():
            if any(term in key.lower() for term in ['price', 'cost', 'total', 'value', 'amount', 'budget']):
                print(f"  - {key}: {value}")
                value_fields_found = True
                
        if not value_fields_found:
            print("  Nessun campo relativo al valore trovato")
                
        # Controlla specificamente il campo price
        print("\n🔍 CONTROLLO SPECIFICO:")
        price = project.get('price')
        print(f"  - Campo 'price': {price} (tipo: {type(price).__name__})")
        
        # Stampa anche i subprojects
        print("\n📋 CONTROLLO SUBPROJECTS:")
        subprojects_path = project.get('subprojects')
        if subprojects_path:
            print(f"  Subprojects URL: {baseUrl}{subprojects_path}")
            try:
                headers = {
                    'Authorization': f'Bearer {apiToken}',
                    'Accept': 'application/json'
                }
                sub_res = requests.get(f"{baseUrl}{subprojects_path}", headers=headers)
                if sub_res.ok:
                    subprojects = sub_res.json().get('data', [])
                    print(f"  Trovati {len(subprojects)} subprojects")
                    # Stampa il primo subproject per vedere cosa contiene
                    if subprojects:
                        print("  Dettagli del primo subproject:")
                        subproject = subprojects[0]
                        print(json.dumps(subproject, indent=4, ensure_ascii=False))
                else:
                    print(f"  Errore recuperando subprojects: {sub_res.status_code}")
            except Exception as e:
                print(f"  Errore recuperando subprojects: {e}")
        else:
            print("  Nessun subproject trovato")
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
