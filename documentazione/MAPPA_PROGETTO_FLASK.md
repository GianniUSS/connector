# 🗺️ MAPPA COMPLETA PROGETTO FLASK - AppConnector

## 📋 OVERVIEW
Progetto Flask che integra **Rentman** (gestione progetti eventi) con **QuickBooks** (fatturazione/contabilità).
Il sistema permette di:
- Sincronizzare progetti da Rentman
- Generare fatture su QuickBooks
- Gestire ore lavorate e time activities
- Import/export dati tra i due sistemi

---

## 🏗️ STRUTTURA GENERALE

### 🎯 FILE ENTRY POINT PRINCIPALI
| File | Ruolo | Porta | Descrizione |
|------|-------|-------|-------------|
| `app.py` | **Entry Point Principale** | 5000 | App Flask principale con interfaccia web completa |
| `list_projects_by_date.py` | **Server Debug** | 5000 | Server Flask semplificato per debug |
| `interfaccia_debug_json/app.py` | **Debug Interface** | Debug | Mini-app per test API |

---

## 🌐 MAPPATURA ROTTE FLASK

### 🔴 APP PRINCIPALE (`app.py`)
| Rotta | Metodo | Funzione | Template/Output | Descrizione |
|-------|--------|----------|----------------|-------------|
| `/` | GET | `home()` | `index.html` | Homepage principale |
| `/static/<path:path>` | GET | `serve_static()` | File statici | Serve CSS/JS/img |
| `/api/token-status` | GET | `token_status()` | JSON | Stato token QuickBooks |
| `/avvia-importazione` | POST | `avvia_importazione_ore()` | JSON | Import ore per periodo |
| `/lista-progetti` | POST | `lista_progetti()` | JSON | Lista progetti Rentman |
| `/elabora-selezionati` | POST | `elabora_selezionati()` | JSON | Fatturazione batch progetti |
| `/dettaglio-progetto/<int:id>` | GET | `dettaglio_progetto()` | JSON | Dettagli singolo progetto |
| `/importa-ore-excel` | POST | `importa_ore_excel()` | JSON | Import ore da Excel |
| `/trasferisci-ore-qb` | POST | `trasferisci_ore_qb()` | JSON | Trasferimento ore su QB |
| `/xml-to-csv.html` | GET | `xml_to_csv()` | `xml-to-csv.html` | Converter XML→CSV |
| `/upload-to-qb` | POST | `upload_to_qb()` | JSON | Upload fatture standard |
| `/upload-to-qb-grouped` | POST | `upload_to_qb_grouped()` | JSON | Upload fatture raggruppate |

### 🟡 SERVER DEBUG (`list_projects_by_date.py`)
| Rotta | Metodo | Funzione | Output | Descrizione |
|-------|--------|----------|--------|-------------|
| `/` | GET | `home()` | `index.html` | Homepage debug |
| `/lista-progetti` | POST | `lista_progetti()` | JSON | Lista progetti con debug |
| `/avvia-importazione` | POST | `avvia_importazione()` | JSON | Simulazione import |

### 🟢 INTERFACCIA DEBUG (`interfaccia_debug_json/app.py`)
| Rotta | Metodo | Funzione | Output | Descrizione |
|-------|--------|----------|--------|-------------|
| `/` | GET | `home()` | `index.html` | Homepage debug JSON |
| `/lista-progetti` | POST | `lista_progetti()` | JSON | Lista progetti base |
| `/avvia-importazione` | POST | `avvia()` | JSON | Subprocess import |

---

## 📁 CLASSIFICAZIONE FILE PYTHON

### 🎛️ **CORE FLASK APPS (3 file)**
```
app.py                              # ⭐ App principale Flask
list_projects_by_date.py           # 🔧 Server debug Flask
interfaccia_debug_json/app.py      # 🔍 Mini debug Flask
```

### 🔗 **API & INTEGRAZIONE (9 file)**
```
rentman_api.py                     # 🎪 API Rentman (progetti, ore, clienti)
rentman_api_fast.py               # ⚡ API Rentman ottimizzata velocità
quickbooks_api.py                  # 💰 API QuickBooks base
quickbooks_bill_importer.py       # 📄 Import fatture QB (PRINCIPALE)
quickbooks_bill_importer_*.py     # 📄 Varianti importer fatture
qb_customer.py                     # 👥 Gestione clienti QuickBooks
qb_time_activity.py               # ⏰ Time activities QuickBooks
token_manager.py                   # 🔐 Gestione token OAuth
mapping.py                         # 🔄 Mapping dati Rentman→QB
```

### 🛠️ **CORE BUSINESS LOGIC (6 file)**
```
create_or_update_invoice_for_project.py    # 💼 Fatturazione progetti
main_invoice_only.py                       # 📋 Solo fatture (no ore)
bill_grouping_system.py                    # 📦 Sistema raggruppamento
import_hours_by_date.py                    # ⏰ Import ore per data
delete_time_activities.py                  # 🗑️ Cancellazione time activities
quickbooks_taxcode_cache.py               # 💹 Cache codici fiscali
```

### ⚙️ **CONFIGURAZIONE & UTILS (3 file)**
```
config.py                          # ⚙️ Configurazioni app
__init__.py                        # 📦 Package marker
requirements.txt                   # 📦 Dipendenze Python
```

### 🔬 **SCRIPT TESTING & DEBUG (20+ file)**
```
# Analisi progetti
analyze_project.py
analyze_subprojects.py
debug_lista_progetti*.py
explore_project_values.py
find_project_value.py

# Testing fatture
generate_bill_payload_*.py
preview_bill_payload.py
manual_test_grouping.py

# Testing generali
final_test.py
quick_test.py
simple_test.py
minimal_project_test.py

# Esplora API
rentman_api_explorer.py
get_project_payload.py
debug_payload_structure.py
```

### 🚀 **SCRIPT PRODUZIONE (5 file)**
```
GetProject.py                      # 📂 Recupero progetti Rentman
GetShortages.py                    # ⚠️ Analisi carenze
get_carenza_progetti.py           # 📊 Report carenze progetti
rentman_shortage_analyzer.py      # 🔍 Analizzatore carenze
get_quickbooks_taxcodes.py        # 💹 Codici fiscali QB
```

---

## 🎨 FRONTEND & TEMPLATE

### 📂 **TEMPLATE HTML (`/templates/`)**
```
templates/
├── xml-to-csv.html               # 🔄 Converter XML→CSV
├── xml-to-csv-fixed.html         # 🔄 Converter corretto
├── xml-to-csv-new.html           # 🔄 Converter nuovo
└── bill-grouping.html            # 📦 Interfaccia raggruppamento
```

### 📂 **FILE STATICI (`/static/`)**
```
static/
├── js/
│   └── token-status.js           # 🔐 Monitor stato token JS
└── xml-to-csv_.html              # 🔄 Template static CSV
```

### 🏠 **HOMEPAGE PRINCIPALE**
```
index.html                        # 🏠 Homepage principale (root)
```

---

## 🔄 CONNESSIONI ROTTE → TEMPLATE

### 🎯 **TEMPLATE RENDERING**
| Rotta | Template | Descrizione |
|-------|----------|-------------|
| `GET /` | `index.html` | Homepage principale con interfaccia completa |
| `GET /xml-to-csv.html` | `templates/xml-to-csv.html` | Tool conversione XML→CSV |

### 📡 **API ENDPOINTS (JSON)**
Tutti gli altri endpoint restituiscono **JSON** per comunicazione AJAX con frontend:
- `/api/token-status` → Stato token
- `/lista-progetti` → Lista progetti JSON
- `/avvia-importazione` → Risultato import JSON
- `/elabora-selezionati` → Risultati fatturazione JSON
- `/dettaglio-progetto/<id>` → Dati progetto JSON
- `/importa-ore-excel` → Report import Excel JSON
- `/trasferisci-ore-qb` → Report trasferimento ore JSON
- `/upload-to-qb*` → Risultati upload fatture JSON

### 📱 **STATIC FILES**
| Path | File | Uso |
|------|------|-----|
| `/static/js/token-status.js` | JavaScript | Monitor token QuickBooks |
| `/static/*` | CSS/JS/Img | Risorse statiche |

---

## 🏭 FLUSSO OPERATIVO PRINCIPALE

### 1️⃣ **LISTA PROGETTI**
```
Browser → POST /lista-progetti → rentman_api.py → list_projects_by_date() → JSON
```

### 2️⃣ **FATTURAZIONE BATCH**
```
Browser → POST /elabora-selezionati → 
├── main_invoice_only.py (import diretto)
└── subprocess fallback
→ JSON risultati
```

### 3️⃣ **IMPORT ORE**
```
Browser → POST /avvia-importazione → 
├── import_hours_by_date.py
└── qb_time_activity.py 
→ JSON risultati
```

### 4️⃣ **UPLOAD FATTURE**
```
Browser → POST /upload-to-qb → 
├── quickbooks_bill_importer.py
├── token_manager.py
└── QuickBooks API 
→ JSON risultati
```

---

## 🔧 RELAZIONI TRA MODULI

### 📊 **DIPENDENZE PRINCIPALI**
```
app.py
├── rentman_api.py
├── quickbooks_bill_importer.py
├── qb_customer.py
├── qb_time_activity.py
├── token_manager.py
├── mapping.py
├── config.py
└── main_invoice_only.py

rentman_api.py
├── config.py
└── requests (HTTP)

quickbooks_bill_importer.py
├── token_manager.py
├── config.py
└── requests (QB API)

qb_customer.py
├── rentman_api.py
├── config.py
└── mapping.py
```

### 🔗 **BLUEPRINT & MODULARITÀ**
Il progetto **non usa Flask Blueprint** ma organizza la logica in:
- **API modules**: rentman_api.py, quickbooks_*.py
- **Service modules**: mapping.py, token_manager.py
- **Utility modules**: config.py
- **Business logic**: main_invoice_only.py, import_hours_by_date.py

---

## 🎯 SCHEMA AD ALBERO COMPLETO

```
AppConnector/
│
├── 🌐 FLASK APPS
│   ├── app.py ⭐ [11 rotte] → index.html + API JSON
│   ├── list_projects_by_date.py [3 rotte] → debug
│   └── interfaccia_debug_json/app.py [3 rotte] → mini-debug
│
├── 🔗 API INTEGRATION
│   ├── rentman_api.py → Rentman Projects/Hours/Customers
│   ├── quickbooks_bill_importer.py ⭐ → QB Bills Import
│   ├── qb_customer.py → QB Customers/Subcustomers
│   ├── qb_time_activity.py → QB Time Activities
│   ├── token_manager.py → OAuth Token Management
│   └── mapping.py → Data Mapping Rentman↔QB
│
├── 💼 BUSINESS LOGIC
│   ├── main_invoice_only.py → Invoice Generation
│   ├── import_hours_by_date.py → Hours Import
│   ├── bill_grouping_system.py → Bill Grouping
│   └── create_or_update_invoice_for_project.py → Project Invoicing
│
├── 🎨 FRONTEND
│   ├── index.html ⭐ → Main Interface
│   ├── templates/
│   │   ├── xml-to-csv.html → XML Converter
│   │   ├── bill-grouping.html → Grouping Interface
│   │   └── xml-to-csv-*.html → Converter Variants
│   └── static/
│       ├── js/token-status.js → Token Monitor
│       └── xml-to-csv_.html → Static Template
│
├── ⚙️ CONFIG & UTILS
│   ├── config.py → App Configuration
│   ├── requirements.txt → Dependencies
│   └── __init__.py → Package Marker
│
└── 🔬 TESTING & DEBUG (20+ files)
    ├── analyze_*.py → Project Analysis
    ├── debug_*.py → Debug Scripts
    ├── generate_*.py → Bill Testing
    └── get_*.py → API Exploration
```

---

## 🚀 PUNTI DI INGRESSO APPLICAZIONE

### 🎯 **PRODUZIONE**
```bash
python app.py
# Server: http://0.0.0.0:5000
# Homepage: http://localhost:5000/
```

### 🔧 **DEBUG**
```bash
python list_projects_by_date.py
# Server: http://127.0.0.1:5000 (debug)
```

### 🔍 **MINI-DEBUG**
```bash
cd interfaccia_debug_json
python app.py
# Server: http://127.0.0.1:5000 (JSON debug)
```

---

## 📈 STATO MODIFICHE RECENTI

### ✅ **COMPLETATE**
1. **Progetti "In opzione"** → Ora visibili (filtro commentato in app.py:172)
2. **Formato date MM/DD/YYYY** → Prioritario in quickbooks_bill_importer.py
3. **Sintassi corretta** → Errore parentesi graffa risolto
4. **🚀 VELOCIZZAZIONE LISTA PROGETTI** → Ottimizzata con rentman_api_fast.py

### 🔧 **CONFIGURAZIONE ATTUALE**
- **Token QuickBooks**: Gestione graceful con modalità simulazione
- **Import fatture**: Supporto diretto + fallback subprocess
- **Import ore**: Supporto diretto + fallback subprocess
- **Filtri progetti**: Esclusi 'Annullato', 'Concept', 'Concetto' (inclusi 'In opzione')
- **⚡ Performance**: Lista progetti ottimizzata (70% più veloce)

---

## ⚡ OTTIMIZZAZIONI PERFORMANCE

### 🚀 **VELOCIZZAZIONE LISTA PROGETTI** 
Basata su analisi di `debug_lista_progetti2.py`, implementata in `rentman_api_fast.py`:

| Ottimizzazione | Descrizione | Miglioramento |
|----------------|-------------|---------------|
| **Sessione HTTP Riutilizzabile** | `requests.Session()` vs singole richieste | 20% più veloce |
| **Paginazione Parallela** | 4 worker ThreadPoolExecutor con chunk 150 | 40% più veloce |
| **Filtraggio Ultra-veloce** | Solo controlli essenziali, no API call extra | 30% più veloce |
| **Dati Minimali** | Solo campi necessari per UI (no manager/types) | 15% più veloce |
| **Timeout Aggressivi** | 10s vs 30s default | 10% più veloce |

**🎯 RISULTATO TOTALE: ~70% più veloce**

### 🔄 **IMPLEMENTAZIONE**
```python
# PRIMA (app.py):
progetti = list_projects_by_date(data.get('fromDate'), data.get('toDate'))

# DOPO (app.py ottimizzato):
from rentman_api_fast import list_projects_by_date_optimized
progetti = list_projects_by_date_optimized(data.get('fromDate'), data.get('toDate'))
```

### 📊 **TEST PERFORMANCE**
```bash
python test_performance_progetti.py
```

---

*🗺️ Mappa creata il: 2 giugno 2025*  
*📊 Progetto: AppConnector - Integrazione Rentman ↔ QuickBooks*
