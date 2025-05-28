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
    projectId = '3488'        # <-- Progetto specifico da verificare
    apiToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJtZWRld2Vya2VyIjoxODYwLCJhY2NvdW50IjoiaXRpbmVyYXBybyIsImNsaWVudF90eXBlIjoib3BlbmFwaSIsImNsaWVudC5uYW1lIjoib3BlbmFwaSIsImV4cCI6MjA1ODU5NzU2MSwiaXNzIjoie1wibmFtZVwiOlwiYmFja2VuZFwiLFwidmVyc2lvblwiOlwiNC43MjguMC4zXCJ9IiwiaWF0IjoxNzQzMDY4MzYxfQ.AqegIhlTftQkz_T4WtJIpTpY1E1_vgNP0uT5SzoNE9w'          # <-- il tuo apiToken
    baseUrl = 'https://api.rentman.net'
    
    output_file = "project_3488_analysis.txt"
    
    try:
        print(f"🔍 Recupero dati per il progetto {projectId}...")
        result = get_project_and_customer(projectId, apiToken, baseUrl)
        
        # Scrivi l'output in un file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"🔍 Recupero dati per il progetto {projectId}...\n")
            
            # Stampa l'intero risultato
            f.write("\n✅ RISULTATO COMPLETO:\n")
            f.write(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Estrai il progetto per analisi
            project = result.get('project', {})
            
            # Stampa solo i campi relativi al valore
            f.write("\n\n💰 CAMPI RELATIVI AL VALORE:\n")
            value_fields_found = False
            for key, value in project.items():
                if any(term in key.lower() for term in ['price', 'cost', 'total', 'value', 'amount', 'budget']):
                    f.write(f"  - {key}: {value}\n")
                    value_fields_found = True
                    
            if not value_fields_found:
                f.write("  Nessun campo relativo al valore trovato\n")
                    
            # Controlla specificamente i campi interessanti
            f.write("\n🔍 CONTROLLO SPECIFICO:\n")
            price = project.get('price')
            project_total_price = project.get('project_total_price')
            project_total_price_cancelled = project.get('project_total_price_cancelled')
            
            f.write(f"  - Campo 'price': {price} (tipo: {type(price).__name__})\n")
            f.write(f"  - Campo 'project_total_price': {project_total_price} (tipo: {type(project_total_price).__name__})\n")
            f.write(f"  - Campo 'project_total_price_cancelled': {project_total_price_cancelled} (tipo: {type(project_total_price_cancelled).__name__})\n")
        
        print(f"✅ Analisi completata. Risultati salvati in {output_file}")
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")
