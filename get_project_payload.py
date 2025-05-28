import requests
import config
import json

def main():
    project_id = 3739
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/projects/{project_id}"
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"Rentman API Error {response.status_code}: {response.text}")
        return
    data = response.json()
    with open("project_3739_api_payload.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Payload completo salvato in project_3739_api_payload.json")
    data = response.json().get('data', {})
    status_path = data.get('status')
    if status_path:
        # Estrai l'ID dallo status_path
        status_id = status_path.split('/')[-1]
        status_url = f"{config.REN_BASE_URL}/statuses/{status_id}"
        status_response = requests.get(status_url, headers=headers)
        if status_response.ok:
            status_payload = status_response.json().get('data', {})
            print("\n--- PAYLOAD STATUS DEL PROGETTO ---")
            print(json.dumps(status_payload, indent=2, ensure_ascii=False))
        else:
            print(f"Errore recuperando status {status_id}: {status_response.status_code}")
    else:
        print("Il progetto non ha un campo status valorizzato.")

if __name__ == "__main__":
    main()
