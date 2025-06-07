# 🏗️ MAPPA STRUTTURALE DETTAGLIATA - AppConnettor

## 📋 INDICE
1. [Architettura Generale](#architettura-generale)
2. [Pagina Principale (index.html)](#pagina-principale)
3. [Pagina XML-to-CSV](#pagina-xml-to-csv)
4. [Endpoint Flask (app.py)](#endpoint-flask)
5. [Relazioni Frontend ↔ Backend](#relazioni-frontend-backend)
6. [Flussi Operativi](#flussi-operativi)
7. [File di Supporto](#file-di-supporto)

---

## 🏢 ARCHITETTURA GENERALE

```
AppConnettor/
├── 🌐 FRONTEND
│   ├── index.html              (Pagina principale progetti)
│   ├── xml-to-csv.html         (Convertitore XML→CSV)
│   └── static/js/
│       └── token-status.js     (Gestione token QuickBooks)
├── 🔧 BACKEND
│   ├── app.py                  (Server Flask principale)
│   ├── rentman_api.py          (API Rentman)
│   ├── qb_*.py                 (Moduli QuickBooks)
│   └── [altri moduli Python]
└── 📊 DATI
    ├── qb_import_status.json   (Status importazioni)
    └── [cache temporanee]
```

---

## 🌐 PAGINA PRINCIPALE (index.html)

### 📐 Layout Struttura
```
┌─────────────────────────────────────────────────────┐
│                    🔗 HEADER                        │
│  Project Integration Manager + Token Status         │
├──────────────┬──────────────────────────────────────┤
│              │              📊 STATS               │
│   SIDEBAR    │  Progetti | Selezionati | Attivi    │
│ CONFIGURAZ.  ├──────────────────────────────────────┤
│              │          🗂️ TABELLA PROGETTI        │
│ • Date       │  ✓ | ID | Num | Nome | Cliente...   │
│ • Excel      │                                      │
│ • Modalità   │                                      │
│ • Pulsanti   │                                      │
└──────────────┴──────────────────────────────────────┘
```

### 🎛️ COMPONENTI SIDEBAR

#### 📅 **Configurazione Date**
- **Elementi DOM**: `#fromDate`, `#toDate`
- **Funzione**: `setDefaultDates()` - imposta date di default
- **Listener**: `change` → `suggestPaginationMode()` - suggerisce modalità paginata per periodi lunghi

#### 📄 **Importazione Excel**
- **Elementi DOM**: `#excelFile`, `#importExcelBtn`, `#importExcelMsg`
- **Funzione**: `importExcelBtn.click` → fetch `/importa-ore-excel`
- **Output**: Modale verifica dati con `renderExcelImportModal()`

#### 🚀 **Modalità Caricamento**
- **Elementi DOM**: `input[name="loadingMode"]`, `#pageSize`
- **Modalità**: 
  - `normal` → endpoint `/lista-progetti`
  - `paginated` → endpoint `/lista-progetti-paginati`
- **Funzione**: `radio.change` → aggiorna UI e testo pulsanti

### 🎯 **Pulsanti Principali**
| Pulsante | ID | Endpoint | Funzione |
|----------|----|---------|---------| 
| Recupera Progetti | `#listProjectsBtn` | `/lista-progetti` o `/lista-progetti-paginati` | `listProjectsBtn.click` |
| Elabora Selezionati | `#processSelectedBtn` | `/elabora-selezionati` | `processSelectedBtn.click` |
| Avvia Importazione | Form submit | `/avvia-importazione` | `importForm.submit` |
| XML→CSV | `#xmlToCsvBtn` | redirect | `window.location.href` |

### 📊 **Area Principale**

#### 🎛️ **Token Status**
- **Elemento DOM**: `#token-status`
- **Endpoint**: `/api/token-status`
- **Script**: `static/js/token-status.js`
- **Stati**: 🟢 Valido | 🟡 Simulazione | 🔴 Errore

#### 📈 **Dashboard Statistiche**
```javascript
// Elementi DOM principali
#totalProjects    // Progetti totali caricati
#selectedProjects // Progetti selezionati dall'utente  
#activeProjects   // Progetti con stato attivo
#loadTime         // Tempo di caricamento in secondi

// Funzione aggiornamento
updateStats(total, selected, active, performanceData)
```

#### 🗂️ **Tabella Progetti**
- **Container**: `#projectList`
- **Checkbox Master**: `#selectAll` → seleziona/deseleziona tutti
- **Righe Dinamiche**: generate da JavaScript
- **Event Listeners**: 
  - `.project-checkbox` → `updateSelectedCount()`
  - `.project-link` → modale dettaglio progetto

### 🎭 **Modali**

#### 📋 **Modale Dettaglio Progetto**
```javascript
// Elemento DOM
#projectModal

// Trigger
click su .project-link

// Endpoint
GET /dettaglio-progetto/{project_id}

// Contenuto
JSON payload completo del progetto
```

#### 📊 **Modale Verifica Excel**
```javascript
// Generata dinamicamente
function renderExcelImportModal(report)

// Mostra tabella con:
// - Project ID, Numero, Fine Progetto
// - Sub-customer, Dipendente, Ore
// - Esito validazione

// Pulsante azione
#openTransferModalBtn → openTransferModal()
```

#### ⬆️ **Modale Trasferimento QuickBooks**
```javascript
// Generata dinamicamente  
function openTransferModal()

// Conferma trasferimento
// Endpoint: POST /trasferisci-ore-qb

// Chain: transferExcelRowsToQb()
```

---

## 📄 PAGINA XML-TO-CSV (xml-to-csv.html)

### 🎯 **Funzionalità Principale**
Conversione file XML fatture elettroniche → CSV QuickBooks

### 🧩 **Componenti**

#### 📂 **Upload File**
```javascript
// Elemento DOM
#xmlFiles (input file multiple)

// Event listener  
xmlFiles.change → updateFileInfo()

// Validazione
- Solo file .xml
- Supporto file multipli
```

#### 🔄 **Conversione**
```javascript
// Pulsante principale
#convertBtn

// Funzione core
async function convertToCSV()

// Processo:
1. Leggi file XML
2. Parse con DOMParser
3. Estrai dati fattura (XPath)
4. Formatta CSV QuickBooks
5. Mostra output
```

#### 📊 **Output CSV**
```javascript
// Area risultato
#csvOutput (textarea)

// Formato CSV QuickBooks:
BillNo,Supplier,BillDate,DueDate,Terms,Location,Memo,Account,LineDescription,LineAmount,LineTaxCode,LineTaxAmount
```

#### 🎛️ **Azioni**
| Pulsante | Funzione | Descrizione |
|----------|----------|-------------|
| Copia | `copyToClipboard()` | Copia CSV negli appunti |
| Scarica | Link dinamico | Download file CSV |
| Invia a QB | `sendToQuickBooks()` | POST `/upload-to-qb` |

### 🔍 **Funzioni Utility XML**
```javascript
getXPath(doc, xpath)        // Estrai testo da XPath
getNodeXPath(node, xpath)   // XPath relativo a nodo
formatCsvField(value)       // Escape caratteri CSV
readFile(file)              // Promise per lettura file
```

---

## 🔧 ENDPOINT FLASK (app.py)

### 🏠 **Endpoint Base**
| Route | Metodo | Descrizione |
|-------|---------|-------------|
| `/` | GET | Serve index.html |
| `/static/<path>` | GET | File statici |
| `/xml-to-csv.html` | GET | Serve pagina conversione |

### 🔑 **API Token**
```python
@app.route('/api/token-status')
def token_status():
    # Verifica validità token QuickBooks
    # Return: {valid: bool, mode: str, message: str}
```

### 📋 **API Progetti**

#### 📊 **Lista Progetti Normale**
```python
@app.route('/lista-progetti', methods=['POST'])
def lista_progetti():
    # Input: {fromDate, toDate}
    # Funzione: list_projects_by_date_unified()
    # Ottimizzazioni: optimize_project_list_loading()
    # Output: {projects: [...]}
```

#### ⚡ **Lista Progetti Paginata**
```python
@app.route('/lista-progetti-paginati', methods=['POST'])  
def lista_progetti_paginati():
    # Input: {fromDate, toDate, pageSize}
    # Funzione: list_projects_by_date_paginated_full_unified()
    # Output: {projects: [...], pagination: {...}}
```

#### 🔍 **Dettaglio Progetto**
```python
@app.route('/dettaglio-progetto/<int:project_id>')
def dettaglio_progetto(project_id):
    # Funzione: get_project_and_customer()
    # Output: payload JSON completo progetto
```

### 💰 **API Fatturazione**

#### ⚡ **Elabora Progetti Selezionati**
```python
@app.route('/elabora-selezionati', methods=['POST'])
def elabora_selezionati():
    # Input: {selectedProjects: [{id, name}, ...]}
    # Processo: parallelo con optimize_selected_projects_processing()
    # Funzione core: main_invoice_only(project_id)
    # Output: {results: [...], summary: {...}}
```

### ⏰ **API Ore**

#### 📥 **Importazione Ore Periodo**
```python
@app.route('/avvia-importazione', methods=['POST'])
def avvia_importazione_ore():
    # Input: {fromDate, toDate, employeeName}
    # Funzione: import_hours_for_period() o subprocess
    # Timeout: 600 secondi (10 minuti)
```

#### 📄 **Importazione Excel**
```python
@app.route('/importa-ore-excel', methods=['POST'])
def importa_ore_excel():
    # Input: FormData (excelFile, data_attivita)
    # Funzione: import_ore_da_excel()
    # Output: report validazione per modale
```

#### ⬆️ **Trasferimento QuickBooks**
```python
@app.route('/trasferisci-ore-qb', methods=['POST'])
def trasferisci_ore_qb():
    # Input: {rows: [validatedRows]}
    # Funzione: inserisci_ore()
    # Output: report finale con sub-customer names
```

### 📄 **API CSV**
```python
@app.route('/upload-to-qb', methods=['POST'])
def upload_to_qb():
    # Input: {csv: csvData}
    # Funzione: parse_csv_to_bills() + create_bills_batch()
    # Output: {success: bool, message: str}
```

---

## 🔗 RELAZIONI FRONTEND ↔ BACKEND

### 📊 **Caricamento Progetti**
```
Frontend                     Backend
────────                     ───────
#listProjectsBtn.click   →   /lista-progetti
  ↓ fetch POST               ↓ list_projects_by_date_unified()
{fromDate, toDate}       →   optimize_project_list_loading()
  ↓                          ↓
updateStats()            ←   {projects: [...]}
renderProjectRows()          
attachCheckboxEvents()
```

### 💰 **Elaborazione Fatture**
```
Frontend                     Backend
────────                     ───────
#processSelectedBtn.click →  /elabora-selezionati
  ↓ fetch POST               ↓ optimize_selected_projects_processing()
{selectedProjects: [...]} →  main_invoice_only(project_id) [parallelo]
  ↓                          ↓ set_qb_import_status()
alert(summary)           ←   {results: [...], summary: {...}}
refreshProjectList()
```

### 📄 **Flusso Excel**
```
Frontend                     Backend
────────                     ───────
#importExcelBtn.click    →   /importa-ore-excel
  ↓ FormData                 ↓ import_ore_da_excel()
{excelFile, data_attivita} → validate_excel_data()
  ↓                          ↓
renderExcelImportModal() ←   {report: [{...validation...}]}
  ↓
#openTransferModalBtn    →   /trasferisci-ore-qb
  ↓ fetch POST               ↓ inserisci_ore()
{rows: [validRows]}      →   update_subcustomer_names()
  ↓                          ↓
alert(success)           ←   {success: bool, report: [...]}
```

### 🔄 **Conversione XML**
```
Frontend (xml-to-csv.html)   Backend
──────────────────────────   ───────
File input change       →   (Local processing)
  ↓ FileReader              
XML parse (DOMParser)        
XPath extraction             
CSV formatting               
  ↓
#sendToQbBtn.click       →   /upload-to-qb
  ↓ fetch POST               ↓ parse_csv_to_bills()
{csv: csvData}           →   create_bills_batch()
  ↓                          ↓
alert(result)            ←   {success: bool, message: str}
```

---

## 🔄 FLUSSI OPERATIVI

### 1️⃣ **Flusso Caricamento Progetti**
```
1. User seleziona date (fromDate, toDate)
2. User sceglie modalità (normale/paginata)
3. Click "Recupera Progetti"
4. suggestPaginationMode() - suggerisce modalità per periodo lungo
5. fetch endpoint appropriato
6. Backend processa progetti con ottimizzazioni
7. Frontend renderizza tabella + statistiche
8. attachCheckboxEvents() per selezione progetti
```

### 2️⃣ **Flusso Elaborazione Fatture**
```
1. User seleziona progetti con checkbox
2. updateSelectedCount() aggiorna contatori
3. Click "Elabora Selezionati"
4. Conferma modale con lista progetti
5. Backend elaborazione parallela fatture
6. set_qb_import_status() per ogni progetto
7. Frontend mostra risultati + aggiorna tabella
```

### 3️⃣ **Flusso Importazione Ore**
```
1. User carica file Excel o imposta periodo
2. Validazione dati (date, employee name)
3. Backend: import_ore_da_excel() o import_hours_for_period()
4. renderExcelImportModal() per verifica dati
5. User conferma trasferimento
6. inserisci_ore() su QuickBooks
7. Mostra risultati finali
```

### 4️⃣ **Flusso XML→CSV**
```
1. User carica file XML multipli
2. updateFileInfo() mostra files selezionati
3. convertToCSV() processa ogni file
4. XML parse + XPath extraction
5. CSV formatting per QuickBooks
6. copyToClipboard() o download o send to QB
7. fetch /upload-to-qb per invio diretto
```

---

## 📁 FILE DI SUPPORTO

### 🔧 **Backend Modules**
```
rentman_api.py           # API Rentman + processing progetti
qb_customer.py           # Gestione Customer/Sub-customer QB
qb_time_activity.py      # Gestione Time Activities QB  
create_or_update_invoice_for_project.py  # Creazione fatture
quickbooks_api.py        # API QuickBooks core
token_manager.py         # Gestione refresh token QB
mapping.py               # Mapping Rentman → QuickBooks
performance_optimizations.py  # Ottimizzazioni caricamento
```

### 📊 **Data Files**
```
qb_import_status.json    # Status import per ogni progetto
config.py                # Configurazioni API keys
requirements.txt         # Dipendenze Python
```

### 📋 **Documentation**
```
MAPPA_PAGINE_E_FUNZIONI.md      # Mapping funzioni JS
MAPPA_STRUTTURA_APPLICAZIONE.md # Struttura generale
README.md                       # Documentazione utente
```

---

## 🎯 **PUNTI CHIAVE INTEGRAZIONE**

### ⚡ **Performance**
- **Caricamento Progetti**: `optimize_project_list_loading()` - batch loading status QB
- **Elaborazione Fatture**: `optimize_selected_projects_processing()` - processing parallelo
- **Modalità Paginata**: riduce memoria per periodi lunghi

### 🔄 **Real-time Updates** 
- **Token Status**: controllo automatico validità token QB
- **Project Status**: aggiornamento stati importazione QB
- **Statistics**: aggiornamento contatori in tempo reale

### 🛡️ **Error Handling**
- **Timeout Management**: 2 min per fatture, 10 min per ore
- **Fallback Systems**: subprocess se import diretti falliscono  
- **Status Tracking**: persistent storage stati importazione

### 🎨 **UI/UX**
- **Responsive Design**: sidebar + main area fluida
- **Loading States**: pulsanti disabilitati durante operazioni
- **Progress Feedback**: messaggi status + performance info
- **Modal Workflows**: conferme e visualizzazione dati

---

Questa mappa strutturale fornisce una visione completa di tutti i componenti dell'applicazione AppConnettor e le loro interazioni, utile per manutenzione, debugging e future espansioni del sistema.
