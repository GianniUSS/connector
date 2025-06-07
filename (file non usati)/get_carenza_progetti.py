import requests
import json
from config import REN_API_TOKEN, REN_BASE_URL

def test_equipment_23971():
    """Test specifico per l'equipment ID 23971 (Stretch Tent)"""
    
    headers = {
        "Authorization": f"Bearer {REN_API_TOKEN}",
        "Accept": "application/json"
    }
    
    equipment_id = 23971
    print(f"\n🔍 TEST DISPONIBILITÀ EQUIPMENT ID: {equipment_id}")
    print("="*60)
    
    # Test 1: Info base equipment
    print("\n1. INFO EQUIPMENT:")
    url = f"{REN_BASE_URL}/equipment/{equipment_id}"
    response = requests.get(url, headers=headers)
    
    if response.ok:
        data = response.json().get("data", {})
        print(f"   Nome: {data.get('displayname') or data.get('name')}")
        print(f"   Quantità totale: {data.get('quantity_total', 'N/A')}")
        print(f"   In magazzino: {data.get('quantity_in_stock', 'N/A')}")
        print(f"   Disponibile: {data.get('quantity_available', 'N/A')}")
        
        # Mostra tutti i campi quantity
        print("\n   Tutti i campi 'quantity':")
        for key, value in data.items():
            if 'quantity' in key.lower() or 'available' in key.lower() or 'stock' in key.lower():
                print(f"   - {key}: {value}")
    else:
        print(f"   Errore: {response.status_code}")
    
    # Test 2: Availability con date diverse
    print("\n2. TEST AVAILABILITY ENDPOINTS:")
    
    test_dates = [
        "2025-06-01",
        "2025-06-02",
        "2025-06-03"
    ]
    
    for date in test_dates:
        print(f"\n   Data: {date}")
        
        # Vari formati di endpoint
        endpoints = [
            f"equipment/{equipment_id}/availability?date={date}",
            f"equipment/{equipment_id}/availability?from={date}&to={date}",
            f"availability?equipment={equipment_id}&date={date}",
            f"equipment/{equipment_id}/stock?date={date}"
        ]
        
        for endpoint in endpoints:
            url = f"{REN_BASE_URL}/{endpoint}"
            try:
                response = requests.get(url, headers=headers)
                if response.ok:
                    print(f"   ✓ {endpoint}: OK")
                    data = response.json()
                    print(f"     Risposta: {json.dumps(data, indent=2)[:200]}...")  # Primi 200 caratteri
                    break
                else:
                    print(f"   ✗ {endpoint}: {response.status_code}")
            except Exception as e:
                print(f"   ✗ {endpoint}: Errore - {str(e)}")
    
    # Test 3: Stock movements
    print("\n3. TEST STOCK MOVEMENTS:")
    url = f"{REN_BASE_URL}/stock_movements?equipment={equipment_id}"
    response = requests.get(url, headers=headers)
    
    if response.ok:
        data = response.json()
        movements = data.get("data", [])
        print(f"   Trovati {len(movements)} movimenti")
        if movements:
            print("   Ultimi 3 movimenti:")
            for mov in movements[:3]:
                print(f"   - Data: {mov.get('date')}, Tipo: {mov.get('type')}, Quantità: {mov.get('quantity')}")
    else:
        print(f"   Errore: {response.status_code}")

if __name__ == "__main__":
    test_equipment_23971()