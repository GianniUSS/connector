# Rentman-QuickBooks Connector

## Descrizione
Applicazione web per integrare Rentman (gestione progetti) con QuickBooks (contabilità), automatizzando la creazione di fatture e la gestione dei clienti.

## Funzionalità
- Sincronizzazione clienti/progetti da Rentman a QuickBooks
- Creazione automatica di fatture per i progetti
- Importazione ore lavorate nei progetti
- Interfaccia web per gestire l'intero processo

## Modalità di funzionamento
L'applicazione può funzionare in due modalità:
1. **Modalità normale**: tutte le funzionalità sono disponibili
2. **Modalità simulazione**: attiva quando il token QuickBooks è scaduto. In questa modalità:
   - L'interfaccia mostra chiaramente che si sta operando in simulazione
   - I clienti e sub-clienti vengono simulati con ID fittizi
   - Le fatture vengono "simulate" ma non create realmente in QuickBooks

## Installazione
1. Clona il repository
2. Installa le dipendenze: `pip install -r requirements.txt`
3. Configura le credenziali nel file `config.py`
4. Avvia l'applicazione: `python app.py`

## Configurazione
Il file `config.py` contiene tutte le configurazioni necessarie:
- Credenziali QuickBooks (Client ID, Client Secret, Refresh Token)
- ID Realm QuickBooks
- Token API Rentman
- URL base Rentman

## Gestione del token QuickBooks
Il token di refresh QuickBooks ha una validità di 100 giorni. Quando scade:
1. Segui le istruzioni in `AGGIORNAMENTO_TOKEN_QUICKBOOKS.md` per ottenere un nuovo token
2. Aggiorna il file `config.py` con il nuovo token

## Risoluzione problemi
Per risolvere problemi comuni, consulta il file `GUIDA_RISOLUZIONE_PROBLEMI.md`

## Test
Sono disponibili diversi script di test:
- `test_token_semplice.py`: verifica lo stato del token QuickBooks
- `test_simulazione_token.py`: testa il funzionamento in modalità simulazione
- `test_token_handling.py`: test completo della gestione dei token

## Autori
Sviluppato per Itinera Pro
