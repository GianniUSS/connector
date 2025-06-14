import sys
import requests
from config import REN_API_TOKEN, REN_BASE_URL

# Intestazioni standard per le chiamate API
HEADERS = {
    "Authorization": f"Bearer {REN_API_TOKEN}",
    "Accept": "application/json"
}

def get_required_items(project_id):
    """
    Recupera la lista di articoli e le quantità richieste per un progetto.
    Usa l'endpoint /content.
    """
    print(f"1. Recupero la lista del materiale richiesto per il progetto {project_id}...")
    url = f"{REN_BASE_URL.rstrip('/')}/projects/{project_id}/content"
    params = {"limit": 200, "offset": 0} # Aumento il limite per ridurre le chiamate
    required_items = []
    
    while True:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status() # Lancia un errore se la chiamata fallisce
        data = response.json().get("data", [])
        
        for entry in data:
            item = entry.get("item", {})
            if item and item.get("id"):
                required_items.append({
                    "item_id": item.get("id"),
                    "item_name": item.get("name", "Nome non trovato"),
                    "required_qty": entry.get("quantity", 0)
                })
        
        # Gestione della paginazione
        next_offset = response.json().get("meta", {}).get("next_offset")
        if next_offset is None:
            break
        params["offset"] = next_offset
        
    print(f"   ✅ Trovati {len(required_items)} tipi di articoli richiesti.\n")
    return required_items

def get_total_stock(equipment_id):
    """
    Recupera la giacenza totale di un singolo articolo dal magazzino.
    Usa l'endpoint /equipment.
    """
    url = f"{REN_BASE_URL.rstrip('/')}/equipment/{equipment_id}"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.ok:
            data = response.json().get("data", {})
            # Il campo 'quantity' in questo endpoint indica la giacenza totale
            return data.get("quantity", 0)
        return 0
    except requests.RequestException:
        return 0

def main():
    if len(sys.argv) < 2:
        print("Utilizzo: python calcolo_giacenza.py <project_id>")
        return
    
    project_id = sys.argv[1]
    
    print(f"\n{'='*60}")
    print(f"⚙️  ANALISI CARENZE BASATA SU GIACENZA TOTALE")
    print(f"{'='*60}\n")
    
    try:
        # 1. Ottieni la lista del materiale del progetto
        required_items = get_required_items(project_id)
        
        if not required_items:
            print("Nessun articolo trovato per questo progetto.")
            return

        print("2. Calcolo le carenze confrontando il richiesto con la giacenza totale...")
        shortages = []
        
        # 2. Per ogni articolo, confronta richiesto vs. giacenza
        for item in required_items:
            required = item["required_qty"]
            if required == 0:
                continue

            stock = get_total_stock(item["item_id"])
            
            if required > stock:
                shortage_details = {
                    "name": item["item_name"],
                    "required": required,
                    "stock": stock,
                    "missing": required - stock
                }
                shortages.append(shortage_details)
        
        print("   ✅ Analisi completata.\n")

        # 3. Mostra i risultati
        print(f"{'-'*60}")
        if not shortages:
            print("✅ Ottime notizie! La tua giacenza totale copre tutto il materiale richiesto.")
        else:
            print(f"⚠️  CARENZE RILEVATE ({len(shortages)} ARTICOLI):")
            for s in shortages:
                print(f"\n❗ {s['name']}")
                print(f"   Richiesti: {s['required']}")
                print(f"   Giacenza totale in magazzino: {s['stock']}")
                print(f"   🔴 MANCANTI IN GIACENZA: {s['missing']} unità")
        print(f"{'-'*60}\n")

    except requests.HTTPError as e:
        print(f"❌ Errore HTTP {e.response.status_code}: {e.response.text}")
    except Exception as e:
        print(f"❌ Si è verificato un errore imprevisto: {e}")

if __name__ == "__main__":
    main()