# REPORT: Implementazione Raggruppamento Righe per Numero Fattura e Fornitore

## Modifiche Effettuate

### 1. Sistema di Raggruppamento (`bill_grouping_system.py`)
- Impostato `by_invoice_and_vendor: True` come valore predefinito
- Questo fa sì che il sistema raggruppi automaticamente le righe che hanno lo stesso numero fattura e fornitore

### 2. Endpoint Anteprima Payload (`app.py`)
- Modificata la logica dell'endpoint `/preview-bill-payload` per raggruppare le righe per numero fattura e fornitore
- Implementato un sistema che raccoglie tutte le righe per ogni combinazione univoca di numero fattura e fornitore
- Genera un payload completo con tutte le righe appartenenti alla stessa fattura

### 3. Struttura Risultato
- Il payload generato ora contiene tutte le righe associate alla stessa fattura
- Ogni riga mantiene le proprie informazioni (importo, descrizione, conto)
- Il payload rispetta la struttura richiesta dall'API QuickBooks

## Verifica e Test
- Creato script di test per verificare il corretto raggruppamento
- Verificato che il payload generato contiene tutte le righe della stessa fattura
- Verificato che la struttura del payload sia conforme alle specifiche QuickBooks

## Risultato Atteso
Quando il sistema riceve dati CSV con più righe che hanno lo stesso numero fattura e fornitore, genererà un unico payload di fattura con tutte le righe corrispondenti, preservando la struttura richiesta dall'API QuickBooks.
