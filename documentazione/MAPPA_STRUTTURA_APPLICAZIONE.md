# 🗺️ MAPPA STRUTTURA APPLICAZIONE - AppConnettor

## 📱 **PAGINA PRINCIPALE** > `index.html`

### 🎯 **Sezioni Principali**

#### 1. **⚙️ Pannello Configurazione** (Sidebar Sinistra)
- **Configurazione Date** 
  - Campo: Data Inizio (`fromDate`)
  - Campo: Data Fine (`toDate`)
  - Funzione: `setDefaultDates()` > `index.html`

- **Modalità Caricamento**
  - Radio: Normale vs Paginata
  - Campo: Page Size (per modalità paginata)
  - Funzione: `suggestPaginationMode()` > `index.html`

- **Importazione Ore da Excel**
  - Upload: File Excel
  - Campo: Data Attività
  - Button: "📤 Importa Ore da Excel"
  - Funzione: `importa_ore_excel()` > `app.py`

- **Conversione XML→CSV**
  - Button: "🔄 Converti XML in CSV"
  - Redirect: `/xml-to-csv.html` > `xml-to-csv.html`

#### 2. **📊 Area Principale** (Content)
- **Header**
  - Titolo: "🚀 Project Integration Manager"
  - Status Token: Check connessione QB
  - Funzione: `token_status()` > `app.py`

- **Statistiche Dashboard**
  - Widget: Progetti Totali
  - Widget: Progetti Selezionati  
  - Widget: Importazione Status
  - Widget: Performance Info

- **Griglia Progetti**
  - Tabella: Lista progetti con checkbox
  - Colonne: ID, Nome, Status, Date, Valore, Cliente, QB Status
  - Funzione: Caricamento progetti

---

## 🔗 **ENDPOINT E FUNZIONI COLLEGATE**

### 📥 **Caricamento Progetti**

#### **Endpoint**: `/lista-progetti` (POST)
- **File**: `app.py` > `lista_progetti()`
- **Dipendenze**:
  - `rentman_projects.py` > `list_projects_by_date_unified()`
  - `performance_optimizations.py` > `optimize_project_list_loading()`
  - `performance_optimizations.py` > `performance_monitor`

#### **Endpoint**: `/lista-progetti-paginati` (POST)  
- **File**: `app.py` > `lista_progetti_paginati()`
- **Dipendenze**:
  - `rentman_projects.py` > `list_projects_by_date_paginated_full_unified()`
  - `performance_optimizations.py` > `optimize_project_list_loading()`

---

### 💰 **Elaborazione Fatture**

#### **Endpoint**: `/elabora-selezionati` (POST)
- **File**: `app.py` > `elabora_selezionati()`
- **Dipendenze**:
  - `create_or_update_invoice_for_project.py` > `create_or_update_invoice_for_project()`
  - `qb_customer.py` > `set_qb_import_status()`, `get_qb_import_status()`
  - `token_manager.py` > Gestione token QB

---

### 🕐 **Importazione Ore**

#### **Endpoint**: `/avvia-importazione` (POST)
- **File**: `app.py` > `avvia_importazione_ore()`
- **Dipendenze**:
  - `import_hours_by_date.py` > `import_hours_for_period()`
  - Fallback subprocess se import diretto fallisce

#### **Endpoint**: `/importa-ore-excel` (POST)
- **File**: `app.py` > `importa_ore_excel()`
- **Dipendenze**:
  - `qb_time_activity.py` > `import_ore_da_excel()`
  - Gestione file temporanei

#### **Endpoint**: `/trasferisci-ore-qb` (POST)
- **File**: `app.py` > `trasferisci_ore_qb()`
- **Dipendenze**:
  - `rentman_api.py` > `get_project_and_customer()`
  - `qb_customer.py` > `trova_o_crea_customer()`, `trova_o_crea_subcustomer()`
  - `mapping.py` > `map_rentman_to_qbo_customer()`, `map_rentman_to_qbo_subcustomer()`
  - `qb_time_activity.py` > `inserisci_ore()`

---

### 📄 **Gestione Dettagli**

#### **Endpoint**: `/dettaglio-progetto/<int:project_id>` (GET)
- **File**: `app.py` > `dettaglio_progetto()`
- **Dipendenze**:
  - `rentman_api.py` > `get_project_and_customer()`

---

### 📊 **Performance Monitoring**

#### **Endpoint**: `/performance-metrics` (GET)
- **File**: `app.py` > `get_performance_metrics()`
- **Dipendenze**:
  - `performance_optimizations.py` > `performance_monitor.get_metrics()`

#### **Endpoint**: `/performance-reset` (POST)
- **File**: `app.py` > `reset_performance_metrics()`
- **Dipendenze**:
  - `performance_optimizations.py` > `performance_monitor.reset_metrics()`

---

### 🔐 **Gestione Token**

#### **Endpoint**: `/api/token-status` (GET)
- **File**: `app.py` > `token_status()`
- **Dipendenze**:
  - `token_manager.py` > `token_manager.is_token_valid()`

---

## 📄 **PAGINA CONVERSIONE XML→CSV** > `xml-to-csv.html`

### 🎯 **Funzionalità**
- **Upload XML**: Carica fatture elettroniche XML
- **Conversione**: Converte XML in formato CSV per QuickBooks
- **Invio QuickBooks**: Due modalità di invio

#### **Modalità Standard**
- **Endpoint**: `/upload-to-qb` (POST)
- **File**: `app.py` > `upload_to_qb()`
- **Dipendenze**:
  - `quickbooks_bill_importer.py` > `QuickBooksBillImporter`
  - `token_manager.py` > `TokenManager`

#### **Modalità Raggruppata**
- **Endpoint**: `/upload-to-qb-grouped` (POST)
- **File**: `app.py` > `upload_to_qb_grouped()`
- **Dipendenze**:
  - `quickbooks_bill_importer.py` > `QuickBooksBillImporter`
  - `bill_grouping_system.py` > Logica raggruppamento fatture

---

## 🔧 **MODULI CORE DI SUPPORTO**

### 📡 **API Rentman**
- **File**: `rentman_api.py`
  - `list_projects_by_date()` - Lista progetti per periodo
  - `get_project_and_customer()` - Dettagli progetto + cliente
  - `get_all_statuses()` - Cache stati progetti

- **File**: `rentman_projects.py` (Sistema Unificato)
  - `list_projects_by_date_unified()` - Versione unificata
  - `list_projects_by_date_paginated_full_unified()` - Con paginazione
  - `get_customer_name_cached()` - Cache nomi clienti
  - `clear_cache()` - Reset cache

### 💼 **API QuickBooks**
- **File**: `quickbooks_api.py`
  - Funzioni base API QuickBooks

- **File**: `qb_customer.py`
  - `trova_o_crea_customer()` - Gestione clienti QB
  - `trova_o_crea_subcustomer()` - Gestione sub-clienti
  - `set_qb_import_status()` - Status import
  - `get_qb_import_status()` - Recupero status

- **File**: `qb_time_activity.py`
  - `import_ore_da_excel()` - Import ore da Excel
  - `inserisci_ore()` - Inserimento ore in QB

### 🔄 **Sistema Fatturazione**
- **File**: `create_or_update_invoice_for_project.py`
  - `create_or_update_invoice_for_project()` - Creazione fatture

- **File**: `quickbooks_bill_importer.py`
  - `QuickBooksBillImporter` - Classe import fatture
  - `create_bill()` - Creazione singola fattura
  - `batch_import_bills()` - Import multiplo
  - `get_vendors()` - Gestione fornitori

### ⚡ **Sistema Ottimizzazioni**
- **File**: `performance_optimizations.py`
  - `optimize_project_list_loading()` - Ottimizzazione caricamento
  - `optimize_selected_projects_processing()` - Ottimizzazione elaborazione
  - `performance_monitor` - Monitoraggio performance

### 🗺️ **Mapping e Configurazione**
- **File**: `mapping.py`
  - `map_rentman_to_qbo_customer()` - Mapping clienti
  - `map_rentman_to_qbo_subcustomer()` - Mapping sub-clienti

- **File**: `config.py`
  - Configurazioni API (QB + Rentman)
  - Credenziali e token

- **File**: `token_manager.py`
  - `TokenManager` - Gestione token QB
  - `get_access_token()` - Recupero token valido
  - `is_token_valid()` - Verifica validità

---

## 🎯 **FLUSSO OPERATIVO PRINCIPALE**

### 1. **Caricamento Progetti**
`index.html` → `/lista-progetti` → `rentman_projects.py` → `performance_optimizations.py`

### 2. **Elaborazione Fatture**  
`index.html` → `/elabora-selezionati` → `create_or_update_invoice_for_project.py` → QuickBooks API

### 3. **Importazione Ore**
`index.html` → `/avvia-importazione` → `import_hours_by_date.py` → `qb_time_activity.py` → QuickBooks API

### 4. **Conversione XML**
`xml-to-csv.html` → `/upload-to-qb` → `quickbooks_bill_importer.py` → QuickBooks API

---

## 📊 **STATISTICHE STRUTTURA**
- **📁 File Principali**: 45 file Python core
- **🌐 Pagine Web**: 2 (index.html + xml-to-csv.html)
- **🔗 Endpoint API**: 12 endpoint Flask
- **🧪 File Test/Debug**: 129 file organizzati in `tests_and_debug/`

---

*Mappa aggiornata il: 6 giugno 2025*
