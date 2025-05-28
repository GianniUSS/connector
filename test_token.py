import token_manager
print("⚠️ Tentativo di refresh token...")
tm = token_manager.TokenManager()
try:
    token = tm.refresh_access_token()
    print(f"✅ Token ottenuto: {token[:10]}...")
except Exception as e:
    print(f"❌ Errore: {e}")
