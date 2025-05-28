# filepath: e:\AppConnettor\token_manager.py
import requests
from requests.auth import HTTPBasicAuth
import config

class TokenManager:
    def __init__(self):
        self.client_id = config.CLIENT_ID
        self.client_secret = config.CLIENT_SECRET
        self.refresh_token = config.REFRESH_TOKEN
        self.redirect_uri = config.REDIRECT_URI
        self.token_url = config.TOKEN_URL
        self.access_token = None
        
    def refresh_access_token(self):
        try:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'redirect_uri': self.redirect_uri
            }
            auth = HTTPBasicAuth(self.client_id, self.client_secret)
            response = requests.post(self.token_url, data=data, auth=auth, headers={
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            })

            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                self.refresh_token = tokens['refresh_token']
                # Salva sempre il nuovo refresh_token! Qui semplificato: puoi scrivere su file/db
                with open(".refresh_token", "w") as f:
                    f.write(self.refresh_token)
                return self.access_token
            else:
                print(f"⚠️ ATTENZIONE: Errore refresh token: {response.status_code}, {response.text}")
                print("🔴 Alcune funzionalità di QuickBooks potrebbero non funzionare correttamente.")
                # Restituiamo un token fittizio per consentire all'applicazione di avviarsi
                return "invalid_token_handled_gracefully"
        except Exception as e:
            print(f"⚠️ ATTENZIONE: Errore durante il refresh del token: {e}")
            print("🔴 Alcune funzionalità di QuickBooks potrebbero non funzionare correttamente.")
            # Restituiamo un token fittizio per consentire all'applicazione di avviarsi
            return "invalid_token_handled_gracefully"

    def get_access_token(self):
        if not self.access_token:
            return self.refresh_access_token()
        return self.access_token

    def load_refresh_token(self):
        # (Se vuoi caricare sempre il refresh_token aggiornato da file)
        try:
            with open(".refresh_token", "r") as f:
                self.refresh_token = f.read().strip()
        except FileNotFoundError:
            pass

# Istanza globale per accesso facilitato
token_manager = TokenManager()
