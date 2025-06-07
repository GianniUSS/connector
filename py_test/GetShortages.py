import sys
import requests
import config

if len(sys.argv) < 2:
    print("Utilizzo: python GetShortages.py <project_id>")
    sys.exit(1)

project_id = sys.argv[1]

# Preparazione header di autenticazione
headers = {
    "Authorization": f"Bearer {config.token}",
    "Accept": "application/json"
}

# Chiamata API per ottenere le attrezzature pianificate del progetto
url = config.base_url + "plannedequipment"  # endpoint API (da confermare secondo la documentazione API)
params = {"project": project_id}
response = requests.get(url, headers=headers, params=params)
if response.status_code != 200:
    print(f"Errore {response.status_code}: {response.text}")
    sys.exit(1)

data = response.json()

# Estrarre la lista di item pianificati; in alcuni casi i dati potrebbero essere sotto chiave "data"
planned_items = data.get("data", data)  # usa data["data"] se esiste, altrimenti usa data stesso

shortages = []  # accumula gli articoli in carenza

for item in planned_items:
    # Ottiene quantità pianificata
    planned_qty = item.get("quantity") or item.get("planned_quantity") or item.get("quantity_planned")
    # Ottiene quantità disponibile/riservata (a seconda di quale campo è presente)
    reserved_qty = item.get("reserved_quantity") or item.get("quantity_reserved")
    available_qty = item.get("available_quantity") or item.get("quantity_available")
    # Determina la quantità effettivamente disponibile per il progetto
    if reserved_qty is not None:
        qty_provided = reserved_qty   # quantità riservata al progetto
    elif available_qty is not None:
        qty_provided = available_qty  # quantità disponibile in magazzino
    else:
        qty_provided = None

    if planned_qty is None or qty_provided is None:
        continue  # salta se dati insufficienti

    if planned_qty > qty_provided:
        missing_qty = planned_qty - qty_provided
        # Nome materiale
        name = item.get("name") or item.get("equipment_name") or "Articolo ID " + str(item.get("id", "sconosciuto"))
        shortages.append((name, planned_qty, qty_provided, missing_qty))

# (Opzionale) recupera il nome del progetto per visualizzarlo
project_name = None
proj_resp = requests.get(config.base_url + f"projects/{project_id}", headers=headers)
if proj_resp.status_code == 200:
    proj_data = proj_resp.json()
    # Se la risposta contiene il progetto (es. sotto "data")
    if proj_data:
        if "data" in proj_data:
            # potenzialmente la risposta è { "data": { ... progetto ... } }
            proj_info = proj_data["data"]
        else:
            proj_info = proj_data
        project_name = proj_info.get("name") or proj_info.get("title")

# Stampa dei risultati
if project_name:
    print(f"Project {project_id}: {project_name}")
else:
    print(f"Project {project_id}")

if shortages:
    print("Carenze rilevate:")
    for name, planned, provided, missing in shortages:
        print(f"- {name}: pianificato {planned}, disponibile {provided}, **mancano {missing}**")
else:
    print("Nessuna carenza di materiale per questo progetto.")
