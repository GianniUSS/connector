import requests
import config
from token_manager import token_manager
import logging

token_manager.load_refresh_token()
access_token = token_manager.get_access_token()

def delete_time_activities_by_customer(subcustomer_id):
    url = f"{config.API_BASE_URL}/v3/company/{config.REALM_ID}/query"
    query = f"SELECT * FROM TimeActivity WHERE CustomerRef = '{subcustomer_id}'"
    params = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        logging.error(f"Errore nella ricerca TimeActivity: {response.status_code} - {response.text}")
        return

    activities = response.json().get("QueryResponse", {}).get("TimeActivity", [])
    if not activities:
        logging.info("Nessuna TimeActivity trovata per il sub-customer.")
        return

    headers["Content-Type"] = "application/json"

    for activity in activities:
        activity_id = activity["Id"]
        sync_token = activity["SyncToken"]
        delete_url = f"{config.API_BASE_URL}{config.REALM_ID}/timeactivity?operation=delete"
        payload = {
            "Id": activity_id,
            "SyncToken": sync_token
        }
        del_resp = requests.post(delete_url, headers=headers, json=payload)
        if del_resp.ok:
            logging.info(f"Cancellata TimeActivity ID: {activity_id}")
        else:
            logging.error(f"Errore cancellazione ID {activity_id}: {del_resp.status_code} - {del_resp.text}")

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("Usage: python delete_time_activities.py <subcustomer_id>")
    else:
        delete_time_activities_by_customer(sys.argv[1])