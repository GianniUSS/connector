import requests
import config
import json

def main():
    status_id = 6  # ID dello status del subproject
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/statuses/{status_id}"
    response = requests.get(url, headers=headers)
    print(f"Risposta grezza API (status code {response.status_code}):\n{response.text}\n")
    if not response.ok:
        print(f"Rentman API Error {response.status_code}: {response.text}")
        return
    data = response.json().get('data', {})
    print("\n--- PAYLOAD STATUS /statuses/6 ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
