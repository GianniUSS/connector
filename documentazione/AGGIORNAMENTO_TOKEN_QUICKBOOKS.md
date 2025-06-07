# Istruzioni per Aggiornare il Token QuickBooks

## Problema
Il token di refresh per QuickBooks è scaduto e deve essere rinnovato. Questo documento fornisce istruzioni dettagliate su come ottenere un nuovo token tramite l'OAuth Playground di Intuit.

## Passo 1: Accedere all'OAuth Playground
1. Vai a [Intuit OAuth Playground](https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl)
2. Accedi con le tue credenziali Intuit (le stesse che usi per accedere a QuickBooks)

## Passo 2: Configurare l'Autorizzazione
1. Nella sezione "Authorization", inserisci le seguenti informazioni:
   - **Client ID**: `ABjSEkHu5eSVDUk43Yk6HPzMqTIqqwy1UIuvFvt46TJq7ekf3Q` (il valore corrente in config.py)
   - **Client Secret**: `3H8yukkptmxZ9JRgbuTgaOPmfbsm5HvSpfDDNQCN` (il valore corrente in config.py)
   - **Redirect URI**: `https://developer.intuit.com/v2/OAuth2Playground/RedirectUrl`
   - **Authorization endpoint**: `https://appcenter.intuit.com/connect/oauth2`
   - **Token endpoint**: `https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`

2. Per gli scope, seleziona:
   - `com.intuit.quickbooks.accounting`
   - `com.intuit.quickbooks.payment`

3. Clicca su "Get Authorization Code"

## Passo 3: Autorizzare l'Applicazione
1. Verrai reindirizzato alla pagina di autorizzazione di Intuit
2. Seleziona l'azienda per la quale vuoi autorizzare l'accesso (deve corrispondere al REALM_ID in config.py)
3. Clicca su "Connetti"

## Passo 4: Ottenere il Token di Refresh
1. Dopo l'autorizzazione, verrai reindirizzato all'OAuth Playground
2. Clicca su "Get Tokens" per ottenere i token di accesso e di refresh
3. Il token di refresh verrà visualizzato nella sezione "Refresh Token"

## Passo 5: Aggiornare il File di Configurazione
1. Copia il nuovo token di refresh dalla sezione "Refresh Token"
2. Apri il file `config.py` nell'applicazione
3. Sostituisci il valore di `REFRESH_TOKEN` con il nuovo token ottenuto
4. Salva il file

## Passo 6: Verificare il Funzionamento
1. Avvia l'applicazione con `python app.py`
2. Verifica che l'applicazione riesca a connettersi correttamente a QuickBooks
3. Se viene visualizzato un messaggio di successo, il token è stato aggiornato correttamente

## Note Importanti
- I token di refresh di Intuit hanno una validità di 100 giorni
- È consigliabile impostare un promemoria per rinnovare il token prima della scadenza
- L'applicazione è stata progettata per funzionare anche con token scaduti, ma alcune funzionalità potrebbero essere limitate
