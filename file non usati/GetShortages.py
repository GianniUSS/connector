import sys
import requests
import config

def get_project_name(project_id, headers):
    url = config.REN_BASE_URL.rstrip("/") + f"/projects/{project_id}"
    response = requests.get(url, headers=headers)
    if response.ok:
        return response.json().get("data", {}).get("name", "Nome non disponibile")
    return "Nome non disponibile"

def main():
    if len(sys.argv) < 2:
        print("Utilizzo: python GetShortages.py <project_id>")
        return

    project_id = sys.argv[1]
    headers = {
        "Authorization": f"Bearer {config.REN_API_TOKEN}",
        "Accept": "application/json"
    }

    # Recupera nome progetto
    project_name = get_project_name(project_id, headers)
    print(f"\n🔎 Verifica carenze per il progetto: {project_name} (ID: {project_id})\n")

    # Chiamata all’endpoint /projects/{id}/plannedequipment
    url = config.REN_BASE_URL.rstrip("/") + f"/projects/{project_id}/plannedequipment"
    response = requests.get(url, headers=headers)
    if not response.ok:
        print(f"❌ Errore {response.status_code}: {response.text}")
        return

    data = response.json().get("data", [])
    shortages = []

    for item in data:
        name = item.get("name") or item.get("equipment_name") or f"ID {item.get('id')}"
        planned = item.get("quantity", 0)
        reserved = item.get("reserved_quantity", 0)

        if reserved is None: reserved = 0
        if planned is None: planned = 0

        if planned > reserved:
            missing = planned - reserved
            shortages.append((name, planned, reserved, missing))

    if shortages:
        print("📦 Materiale in carenza:")
        for name, planned, reserved, missing in shortages:
            print(f"- {name}: pianificato {planned}, riservato {reserved}, ❗ mancano {missing}")
    else:
        print("✅ Nessuna carenza di materiale per questo progetto.")

if __name__ == "__main__":
    main()
