# Risoluzione Problemi Applicazione Rentman-QuickBooks

## Problemi Risolti

1. **Correzione del file create_or_update_invoice_for_project.py**
   - Aggiunta la dichiarazione `__all__` per esportare correttamente la funzione principale
   - Aggiunta documentazione al modulo per migliorare la leggibilità
   - Migliorata la gestione degli errori nelle richieste API

2. **Miglioramento gestione token QuickBooks**
   - Il file `token_manager.py` è stato modificato per gestire in modo elegante i token scaduti
   - L'applicazione può avviarsi anche con token non validi, restituendo risposte simulate

3. **Miglioramento gestione clienti e sub-clienti**
   - Corretto il problema dei sub-clienti aggiungendo il campo `Job = True`
   - Aggiunti campi personalizzati richiesti da QuickBooks

## Configurazione e Preparazione

1. **Configurazione Ambiente Python**
   - Assicurati di utilizzare l'ambiente Python corretto con tutti i pacchetti necessari
   - Esegui `pip install -r requirements.txt` per installare tutte le dipendenze

2. **Aggiornamento Token QuickBooks**
   - Segui le istruzioni nel file `AGGIORNAMENTO_TOKEN_QUICKBOOKS.md` per ottenere un nuovo token
   - Aggiorna il file `config.py` con il nuovo token di refresh

3. **Verifica Funzionalità**
   - Avvia l'applicazione con `python app.py`
   - Controlla che non ci siano errori durante l'avvio
   - Testa l'importazione di progetti e la creazione di fatture

## Procedura per l'Avvio

1. **Verificare l'Ambiente**
   ```powershell
   # Verificare che Flask e altre dipendenze siano installate
   pip list
   
   # Se manca Flask, installarlo
   pip install flask requests
   ```

2. **Avviare l'Applicazione**
   ```powershell
   cd "percorso\dell'applicazione"
   python app.py
   ```

3. **Accedere all'Interfaccia Web**
   - Apri un browser e vai a `http://localhost:5000`
   - Usa l'interfaccia per selezionare e processare i progetti

## Note sulla Gestione dei Token

L'applicazione è stata modificata per funzionare anche con token scaduti, operando in "modalità simulazione":

1. Con token valido: 
   - Tutte le funzionalità sono disponibili
   - Le fatture vengono effettivamente create/aggiornate in QuickBooks

2. Con token scaduto (modalità simulazione):
   - L'applicazione si avvia normalmente
   - I clienti e sub-clienti vengono simulati con ID fittizi
   - Le fatture vengono "simulate" ma non create realmente in QuickBooks
   - L'interfaccia utente mostra chiaramente quali operazioni sono state simulate
   - Il formato dell'ID fattura simulata è "simulato_XXXX" dove XXXX è l'ID del progetto

Questa modalità è utile per:
- Testare l'applicazione senza interagire con QuickBooks
- Continuare a utilizzare l'applicazione anche quando il token è scaduto
- Visualizzare in anteprima le fatture che verranno create dopo il rinnovo del token

## Suggerimenti per il Futuro

1. **Implementare Notifiche Token**
   - Aggiungere un sistema di notifica quando il token sta per scadere
   - Visualizzare un avviso nell'interfaccia quando il token è scaduto

2. **Migliorare la Modalità Offline**
   - Implementare una modalità offline completa che salvi le operazioni in sospeso
   - Sincronizzare automaticamente quando la connessione è ripristinata

3. **Automatizzare il Rinnovo del Token**
   - Sviluppare un processo automatico per il rinnovo del token
   - Eliminare la necessità di intervento manuale ogni 100 giorni
