import requests
import config
import json

def main():
    headers = {
        'Authorization': f'Bearer {config.REN_API_TOKEN}',
        'Accept': 'application/json'
    }
    url = f"{config.REN_BASE_URL}/projects"
    print(f"🔍 Chiamata API: {url}")
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"❌ Errore API: {response.status_code} - {response.text}")
        return
    projects = response.json().get('data', [])
    print(f"📋 Progetti totali ricevuti: {len(projects)}")
    found = False
    for p in projects:
        if str(p.get('id')) == '3488':
            found = True
            print("\n🎯 PROGETTO 3488 TROVATO NELLA LISTA!")
            for key, value in p.items():
                if any(term in key.lower() for term in ['price', 'cost', 'total', 'value']):
                    print(f"  - {key}: {value} (tipo: {type(value).__name__})")
            print(f"\nTUTTO IL DIZIONARIO:\n{json.dumps(p, indent=2, ensure_ascii=False)}")
    if not found:
        print("❌ Progetto 3488 NON trovato nella lista!")

if __name__ == "__main__":
    main()
