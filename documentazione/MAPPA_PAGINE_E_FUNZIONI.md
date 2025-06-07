# 🗺️ MAPPA DETTAGLIATA PAGINE E FUNZIONI - AppConnettor

## 📱 **PAGINA PRINCIPALE** > `index.html`

### 🎯 **PANORAMICA PAGINA**
- **URL**: `/` (`http://localhost:5000`)
- **Titolo**: "Rentman Project Manager"
- **Layout**: Sidebar + Area Principale
- **Framework**: Vanilla JavaScript + CSS Grid/Flexbox

---

### 🧩 **COMPONENTI E FUNZIONI JAVASCRIPT**

#### 1. **⚙️ SIDEBAR CONFIGURAZIONE**

##### **📅 Gestione Date**
```javascript
// Funzioni: index.html (linea 408)
function setDefaultDates() {
  // Imposta data odierna come default
  const today = new Date();
  const todayString = today.toISOString().split('T')[0];
  document.getElementById("fromDate").value = todayString;
  document.getElementById("toDate").value = todayString;
}

function suggestPaginationMode() {
  // Suggerisce modalità paginata per periodi > 60 giorni
  const daysDiff = Math.ceil((to - from) / (1000 * 60 * 60 * 24));
  if (daysDiff > 60) {
    document.getElementById('paginatedMode').checked = true;
    showPerformanceTip(daysDiff);
  }
}
```
- **Elementi DOM**: `#fromDate`, `#toDate`
- **Endpoint collegati**: Tutti gli endpoint di caricamento progetti

##### **🚀 Modalità Caricamento**
```javascript
// Event Listeners: index.html (linea 725)
document.querySelectorAll('input[name="loadingMode"]').forEach(function(radio) {
  radio.addEventListener('change', function() {
    const isPaginated = this.value === 'paginated';
    pageSize.disabled = !isPaginated;
    // Aggiorna il testo del pulsante
    if (isPaginated) {
      btn.innerHTML = '<span>⚡</span> Recupera Lista Progetti (Paginato)';
    } else {
      btn.innerHTML = '<span>📋</span> Recupera Lista Progetti';
    }
  });
});
```
- **Elementi DOM**: `input[name="loadingMode"]`, `#pageSize`
- **Endpoint**: `/lista-progetti` (normale), `/lista-progetti-paginati` (paginata)

##### **📤 Importazione Ore da Excel**
```javascript
// Event Listener: index.html (linea 1054)
document.getElementById('importExcelBtn').addEventListener('click', function() {
  const file = fileInput.files[0];
  const dataAttivita = document.getElementById('toDate').value;
  
  // Validazione
  if (!file || !dataAttivita) return;
  
  // Upload con FormData
  const formData = new FormData();
  formData.append('excelFile', file);
  formData.append('data_attivita', dataAttivita);
  
  fetch('/importa-ore-excel', {
    method: 'POST',
    body: formData
  })
  .then(response => handleExcelImportResponse(response));
});
```
- **Elementi DOM**: `#excelFile`, `#importExcelBtn`, `#importExcelMsg`
- **Endpoint**: `/importa-ore-excel` (POST)

---

#### 2. **📊 AREA PRINCIPALE**

##### **🔐 Status Token QuickBooks**
```javascript
// File: static/js/token-status.js (linea 14)
function checkTokenStatus() {
  fetch('/api/token-status')
    .then(response => response.json())
    .then(data => {
      tokenStatusElement.classList.remove('token-valid', 'token-invalid', 'token-error');
      
      if (data.valid) {
        tokenStatusElement.textContent = '✅ ' + data.message;
        tokenStatusElement.classList.add('token-valid');
      } else if (data.mode === 'simulazione') {
        tokenStatusElement.textContent = '⚠️ ' + data.message;
        tokenStatusElement.classList.add('token-invalid');
      } else {
        tokenStatusElement.textContent = '❌ ' + data.message;
        tokenStatusElement.classList.add('token-error');
      }
    });
}
```
- **Elementi DOM**: `#token-status`
- **Endpoint**: `/api/token-status` (GET)
- **Auto-refresh**: Ogni 5 minuti

##### **📊 Dashboard Statistiche**
```javascript
// Funzione: index.html (linea 478)
function updateStats(total, selected, active, performanceData) {
  document.getElementById('totalProjects').textContent = total || 0;
  document.getElementById('selectedProjects').textContent = selected || 0;
  document.getElementById('activeProjects').textContent = active || 0;
  
  // Performance metrics
  if (performanceData && performanceData.loadTime) {
    document.getElementById('loadTime').textContent = performanceData.loadTime + 's';
  }
  
  // Barra performance
  if (performanceData && performanceData.speed && performanceData.projects > 0) {
    const performanceText = document.getElementById('performanceText');
    performanceText.innerHTML = `
      ⚡ <strong>${performanceData.projects}</strong> progetti caricati in 
      <strong>${performanceData.loadTime}s</strong> 
      (<strong>${performanceData.speed}</strong> progetti/sec)
    `;
  }
}
```
- **Elementi DOM**: `#totalProjects`, `#selectedProjects`, `#activeProjects`, `#loadTime`, `#performanceInfo`

##### **📋 Griglia Progetti - Caricamento**
```javascript
// Event Listener: index.html (linea 745)
document.getElementById("listProjectsBtn").addEventListener("click", function() {
  const from = document.getElementById("fromDate").value;
  const to = document.getElementById("toDate").value;
  
  // Determina modalità e endpoint
  const loadingMode = document.querySelector('input[name="loadingMode"]:checked').value;
  const isPaginated = loadingMode === 'paginated';
  const endpoint = isPaginated ? '/lista-progetti-paginati' : '/lista-progetti';
  const pageSize = isPaginated ? parseInt(document.getElementById('pageSize').value) : null;
  
  // Prepara payload
  const requestBody = isPaginated 
    ? { fromDate: from, toDate: to, pageSize: pageSize }
    : { fromDate: from, toDate: to };
  
  fetch(endpoint, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(requestBody)
  })
  .then(response => renderProjectList(response));
});
```
- **Elementi DOM**: `#listProjectsBtn`, `#projectList tbody`
- **Endpoint**: `/lista-progetti` (POST), `/lista-progetti-paginati` (POST)

##### **📋 Griglia Progetti - Rendering**
```javascript
// Funzione: index.html (linea 855)
js.projects.forEach(function(p, index) {
  const statusBadge = getStatusBadge(p.status);
  const tr = document.createElement("tr");
  
  tr.innerHTML = `
    <td><input type="checkbox" class="project-checkbox" data-project-id="${p.id}" data-project-name="${p.name}"></td>
    <td><strong>${p.id || 'N/A'}</strong></td>
    <td><code>${p.number || 'N/A'}</code></td>
    <td><a href="#" class="project-link" data-project-id="${p.id}">${p.name || 'N/A'}</a></td>
    <td>${p.customer || '-'}</td>
    <td>${statusBadge}</td>
    <td>${p.manager_name || 'N/A'}</td>
    <td>€ ${p.project_value || 'N/A'}</td>
    <td>${renderQbImportStatus(p.qb_import)}</td>
  `;
  
  tbody.appendChild(tr);
});

// Collega eventi
attachCheckboxEvents();
attachProjectLinkEvents();
```

##### **☑️ Gestione Selezione Progetti**
```javascript
// Funzioni: index.html (linea 517, 955)
function attachCheckboxEvents() {
  document.querySelectorAll('.project-checkbox').forEach(function(checkbox) {
    checkbox.addEventListener('change', function() {
      const row = this.closest('tr');
      if (this.checked) {
        row.classList.add('selected-row');
      } else {
        row.classList.remove('selected-row');
      }
      updateSelectedCount();
    });
  });
}

// Seleziona tutti
document.getElementById('selectAll').addEventListener('change', function() {
  const checkboxes = document.querySelectorAll('.project-checkbox');
  checkboxes.forEach(function(checkbox, index) {
    checkbox.checked = this.checked;
    // Aggiorna visual feedback
    if (this.checked) {
      rows[index].classList.add('selected-row');
    } else {
      rows[index].classList.remove('selected-row');
    }
  }.bind(this));
  updateSelectedCount();
});
```
- **Elementi DOM**: `.project-checkbox`, `#selectAll`, `#selectedCount`

##### **💰 Elaborazione Fatture**
```javascript
// Event Listener: index.html (linea 975)
document.getElementById('processSelectedBtn').addEventListener('click', function() {
  const selectedCheckboxes = document.querySelectorAll('.project-checkbox:checked');
  const selectedProjects = Array.from(selectedCheckboxes).map(function(checkbox) {
    return {
      id: checkbox.dataset.projectId,
      name: checkbox.dataset.projectName
    };
  });
  
  if (selectedProjects.length === 0) {
    alert('⚠️ Nessun progetto selezionato!');
    return;
  }
  
  const confirmed = confirm(`💰 Elaborare FATTURE per ${selectedProjects.length} progetti selezionati?`);
  if (confirmed) {
    fetch('/elabora-selezionati', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ selectedProjects: selectedProjects })
    })
    .then(response => handleInvoiceProcessingResponse(response));
  }
});
```
- **Elementi DOM**: `#processSelectedBtn`
- **Endpoint**: `/elabora-selezionati` (POST)

##### **🕐 Importazione Ore (Form principale)**
```javascript
// Event Listener: index.html (linea 671)
document.getElementById("importForm").addEventListener("submit", function(e) {
  e.preventDefault();
  const from = document.getElementById("fromDate").value;
  const to = document.getElementById("toDate").value;
  
  const employeeName = prompt('👤 Inserisci il nome dell employee per le ore:', 'GINUDDO');
  if (!employeeName) {
    alert('❌ Nome employee richiesto per importare le ore');
    return;
  }
  
  const confirmed = confirm(`🕐 Importare ore per tutti i progetti dal ${from} al ${to}?`);
  if (confirmed) {
    fetch("/avvia-importazione", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ fromDate: from, toDate: to, employeeName: employeeName })
    })
    .then(response => handleHoursImportResponse(response));
  }
});
```
- **Elementi DOM**: `#importForm`
- **Endpoint**: `/avvia-importazione` (POST)

---

#### 3. **🔍 MODALI E DETTAGLI**

##### **📄 Modale Dettaglio Progetto**
```javascript
// Event Listener: index.html (linea 917)
document.querySelectorAll('.project-link').forEach(function(link) {
  link.addEventListener('click', function(e) {
    e.preventDefault();
    const projectId = this.dataset.projectId;
    const modal = document.getElementById('projectModal');
    const pre = document.getElementById('projectPayload');
    
    pre.textContent = 'Caricamento...';
    modal.style.display = 'flex';
    
    fetch('/dettaglio-progetto/' + encodeURIComponent(projectId))
      .then(r => r.json())
      .then(data => {
        pre.textContent = JSON.stringify(data, null, 2);
      })
      .catch(err => {
        pre.textContent = 'Errore nel caricamento del payload: ' + err;
      });
  });
});
```
- **Elementi DOM**: `.project-link`, `#projectModal`, `#projectPayload`
- **Endpoint**: `/dettaglio-progetto/<int:project_id>` (GET)

##### **📊 Modale Verifica Excel**
```javascript
// Funzione: index.html (linea 543)
async function renderExcelImportModal(report) {
  // Recupera dettagli progetto per ogni riga
  for (const r of report) {
    if (!r.subcustomer_name || !r.project_number || !r.project_end) {
      const details = await getProjectDetails(r.project_id);
      r.subcustomer_name = details.subcustomer_name || r.subcustomer_name;
      r.project_number = details.project_number || '';
      r.project_end = details.project_end || '';
    }
  }
  
  // Genera HTML tabella
  let html = `<div>
    <h3>Verifica dati importati da Excel</h3>
    <table>
      <thead>
        <tr><th>Project ID</th><th>Numero Progetto</th><th>Fine Progetto</th><th>Sub-customer</th><th>Dipendente</th><th>Ore</th><th>Esito</th></tr>
      </thead>
      <tbody>`;
  
  for (const r of report) {
    html += `<tr><td>${r.project_id}</td><td>${r.project_number}</td><td>${r.project_end}</td><td>${r.subcustomer_name}</td><td>${r.employee_name}</td><td>${r.ore}</td><td style="color:${r.esito==='OK'?'#27ae60':'#e74c3c'};">${r.esito}</td></tr>`;
  }
  
  html += `</tbody></table>
    <div style="margin-top:2em;text-align:right;">
      <button id="closeExcelImportModalBtn">Chiudi</button>
      <button id="openTransferModalBtn">⬆️ Trasferisci su QuickBooks</button>
    </div></div>`;
  
  const modal = document.getElementById('excelImportModal');
  modal.innerHTML = html;
  modal.style.display = 'flex';
}
```
- **Elementi DOM**: `#excelImportModal`
- **Funzioni collegate**: `getProjectDetails()`, `openTransferModal()`

##### **⬆️ Trasferimento Ore su QuickBooks**
```javascript
// Funzione: index.html (linea 635)
function transferExcelRowsToQb() {
  const okRows = lastExcelImportReport.filter(r => r.esito === 'OK');
  
  if (okRows.length === 0) {
    alert('Nessuna riga valida da trasferire su QuickBooks.');
    return;
  }
  
  const btn = document.getElementById('transferToQbBtn') || document.getElementById('openTransferModalBtn');
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '⏳ Trasferimento in corso...';
  
  fetch('/trasferisci-ore-qb', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ rows: okRows })
  })
  .then(r => r.json())
  .then(js => {
    btn.disabled = false;
    btn.innerHTML = originalText;
    
    if (js.success) {
      lastExcelImportReport = js.report;
      renderExcelImportModal(js.report);
      alert('✅ Trasferimento completato!');
    } else {
      alert('❌ Errore trasferimento: ' + (js.error || js.message || 'Errore sconosciuto'));
    }
  });
}
```
- **Endpoint**: `/trasferisci-ore-qb` (POST)

---

#### 4. **🔄 FUNZIONI UTILITY**

##### **🎨 Status Badge**
```javascript
// Funzione: index.html (linea 463)
function getStatusBadge(status) {
  const badges = {
    'Confermato': 'badge-success',
    'In location': 'badge-info',
    'Pronto': 'badge-warning',
    'Rientrato': 'badge-secondary',
    'Annullato': 'badge-secondary',
    'Concept': 'badge-warning',
    'In opzione': 'badge-info'
  };
  
  const badgeClass = badges[status] || 'badge-secondary';
  return '<span class="badge ' + badgeClass + '">' + (status || 'N/A') + '</span>';
}
```

##### **📊 Status QuickBooks Import**
```javascript
// Funzione: index.html (linea 1113)
function renderQbImportStatus(qbImport) {
  if (!qbImport) return '<span style="color:#888;">-</span>';
  
  if (qbImport.status === 'success' || qbImport.status === 'success_simulated') {
    return '<span style="color:#27ae60;font-weight:bold;">OK</span>' + 
           (qbImport.timestamp ? '<br><span style="font-size:0.8em;color:#888;">' + 
           qbImport.timestamp.replace('T',' ') + '</span>' : '');
  }
  if (qbImport.status === 'timeout') {
    return '<span style="color:#e67e22;font-weight:bold;">Timeout</span>' + 
           (qbImport.timestamp ? '<br><span style="font-size:0.8em;color:#888;">' + 
           qbImport.timestamp.replace('T',' ') + '</span>' : '');
  }
  if (qbImport.status === 'error') {
    return '<span style="color:#e74c3c;font-weight:bold;">Errore</span>' + 
           (qbImport.message ? '<br><span style="font-size:0.85em;color:#e74c3c;">' + 
           qbImport.message + '</span>' : '') + 
           (qbImport.timestamp ? '<br><span style="font-size:0.8em;color:#888;">' + 
           qbImport.timestamp.replace('T',' ') + '</span>' : '');
  }
  
  return '<span style="color:#888;">-</span>';
}
```

##### **🔍 Recupero Dettagli Progetto**
```javascript
// Funzione: index.html (linea 531)
async function getProjectDetails(projectId) {
  try {
    const resp = await fetch('/dettaglio-progetto/' + encodeURIComponent(projectId));
    if (!resp.ok) return {};
    const data = await resp.json();
    return {
      subcustomer_name: (data && data.project && data.project.name) ? data.project.name : '',
      project_number: (data && data.project && data.project.number) ? data.project.number : '',
      project_end: (data && data.project && data.project.equipment_period_to) ? data.project.equipment_period_to : ''
    };
  } catch (e) {
    return {};
  }
}
```
- **Endpoint**: `/dettaglio-progetto/<int:project_id>` (GET)

---

## 📄 **PAGINA CONVERSIONE XML→CSV** > `xml-to-csv.html`

### 🎯 **PANORAMICA PAGINA**
- **URL**: `/xml-to-csv.html`
- **Titolo**: "Convertitore XML a CSV per QuickBooks"
- **Servita da**: Flask route `/xml-to-csv.html` → `templates/xml-to-csv.html`
- **Scopo**: Conversione fatture XML in formato CSV per QuickBooks

---

### 🧩 **COMPONENTI E FUNZIONI JAVASCRIPT**

#### 1. **📤 Upload e Conversione File**
```javascript
// File: templates/xml-to-csv.html (linea 428+)
function appInit() {
  // Event listeners
  xmlFilesInput.addEventListener('change', updateFileInfo);
  convertBtn.addEventListener('click', convertXmlToCsv);
  copyBtn.addEventListener('click', copyToClipboard);
  sendToQbBtn.addEventListener('click', sendCsvToQuickBooks);
  
  // Torna alla pagina principale
  document.getElementById('helpBtn').addEventListener('click', function() {
    window.location.href = '/';
  });
}

function updateFileInfo() {
  const files = xmlFilesInput.files;
  if (files.length > 0) {
    let info = files.length + ' file(i) selezionato(i):\n';
    for (let i = 0; i < files.length; i++) {
      info += '• ' + files[i].name + ' (' + (files[i].size / 1024).toFixed(2) + ' KB)\n';
    }
    fileInfo.textContent = info;
    convertBtn.disabled = false;
  } else {
    fileInfo.textContent = 'Nessun file selezionato';
    convertBtn.disabled = true;
  }
}
```

#### 2. **⚙️ Conversione XML→CSV**
```javascript
function convertXmlToCsv() {
  const files = xmlFilesInput.files;
  if (files.length === 0) return;
  
  convertBtn.disabled = true;
  convertBtn.textContent = 'Conversione in corso...';
  statusMsg.textContent = '';
  csvOutput.value = '';
  
  // Processa ogni file XML
  processAllFiles(files).then(csvData => {
    csvOutput.value = csvData;
    copyBtn.disabled = false;
    sendToQbBtn.disabled = false;
    
    // Genera link download
    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    downloadLink.href = url;
    downloadLink.download = 'fatture_quickbooks.csv';
    downloadLink.style.display = 'inline-block';
    
    statusMsg.textContent = '✅ Conversione completata con successo!';
    statusMsg.className = 'status success';
  }).catch(error => {
    statusMsg.textContent = '❌ Errore durante la conversione: ' + error.message;
    statusMsg.className = 'status error';
  }).finally(() => {
    convertBtn.disabled = false;
    convertBtn.textContent = 'Converti in CSV';
  });
}
```

#### 3. **📋 Copia negli Appunti**
```javascript
function copyToClipboard() {
  csvOutput.select();
  csvOutput.setSelectionRange(0, 99999);
  
  try {
    document.execCommand('copy');
    statusMsg.textContent = '✅ CSV copiato negli appunti!';
    statusMsg.className = 'status success';
  } catch (err) {
    statusMsg.textContent = '❌ Errore nella copia: ' + err;
    statusMsg.className = 'status error';
  }
}
```

#### 4. **📨 Invio a QuickBooks**
```javascript
function sendCsvToQuickBooks() {
  const csvData = csvOutput.value;
  if (!csvData.trim()) {
    alert('⚠️ Nessun dato CSV da inviare');
    return;
  }
  
  sendToQbBtn.disabled = true;
  sendToQbBtn.textContent = 'Invio in corso...';
  
  // Determina modalità di invio
  const selectedMode = document.querySelector('input[name="sendMode"]:checked').value;
  
  // Prepara payload in base alla modalità selezionata
  const payload = {
    csv_data: csvData,
    mode: selectedMode,
    grouping_enabled: selectedMode === 'grouped'
  };
  
  fetch('/api/import-bills-csv', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      statusMsg.textContent = '✅ Fatture inviate con successo a QuickBooks!';
      statusMsg.className = 'status success';
      
      // Mostra dettagli risultato
      if (data.details) {
        statusMsg.textContent += '\n' + data.details;
      }
    } else {
      statusMsg.textContent = '❌ Errore nell\'invio: ' + (data.error || 'Errore sconosciuto');
      statusMsg.className = 'status error';
    }
  })
  .catch(error => {
    statusMsg.textContent = '❌ Errore di connessione: ' + error.message;
    statusMsg.className = 'status error';
  })
  .finally(() => {
    sendToQbBtn.disabled = false;
    sendToQbBtn.textContent = 'Invia a QuickBooks';
  });
}
```

#### 5. **🏷️ Elementi DOM Principali**
- **Upload**: `#xmlFiles` (input file multiple)
- **Info File**: `#fileInfo` (display info file selezionati)
- **Conversione**: `#convertBtn` (trigger conversione)
- **Output**: `#csvOutput` (textarea risultato CSV)
- **Azioni**: `#copyBtn`, `#downloadLink`, `#sendToQbBtn`
- **Status**: `#statusMsg` (messaggi di stato)
- **Modalità**: `input[name="sendMode"]` (radio buttons)
- **Torna Home**: `#helpBtn`

---

## 🔌 **ENDPOINT FLASK COLLEGATI**

### 📥 **Caricamento Progetti**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/lista-progetti` | POST | `lista_progetti()` | `listProjectsBtn.click` |
| `/lista-progetti-paginati` | POST | `lista_progetti_paginati()` | `listProjectsBtn.click` (modalità paginata) |

### 💰 **Elaborazione Fatture**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/elabora-selezionati` | POST | `elabora_selezionati()` | `processSelectedBtn.click` |

### 🕐 **Importazione Ore**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/avvia-importazione` | POST | `avvia_importazione_ore()` | `importForm.submit` |
| `/importa-ore-excel` | POST | `importa_ore_excel()` | `importExcelBtn.click` |
| `/trasferisci-ore-qb` | POST | `trasferisci_ore_qb()` | `transferExcelRowsToQb()` |

### 📄 **Gestione Dettagli**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/dettaglio-progetto/<id>` | GET | `dettaglio_progetto()` | `project-link.click`, `getProjectDetails()` |

### 🔐 **Sistema**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/api/token-status` | GET | `token_status()` | `checkTokenStatus()` (auto-refresh) |
| `/xml-to-csv.html` | GET | `xml_to_csv()` | redirect da `xmlToCsvBtn.click` |

### 📊 **Conversione XML→CSV**
| Endpoint | Metodo | Funzione Flask | Funzione JS |
|----------|--------|----------------|-------------|
| `/api/import-bills-csv` | POST | `parse_csv_to_bills()` | `sendCsvToQuickBooks()` |

---

## 🔄 **FLUSSI OPERATIVI PRINCIPALI**

### 1. **🚀 Caricamento Progetti**
```
fromDate/toDate → loadingMode → listProjectsBtn.click() 
  → fetch(endpoint) → renderProjectList() → attachEvents() 
  → updateStats()
```

### 2. **💰 Elaborazione Fatture**
```
selectProjects → processSelectedBtn.click() → confirm() 
  → fetch('/elabora-selezionati') → handleResponse() 
  → updateProjectList()
```

### 3. **🕐 Importazione Ore (Excel)**
```
selectExcelFile → importExcelBtn.click() → upload 
  → fetch('/importa-ore-excel') → renderExcelImportModal() 
  → transferToQb() → fetch('/trasferisci-ore-qb')
```

### 4. **🔄 Conversione XML→CSV**
```
selectXmlFiles → convertBtn.click() → processXML() 
  → generateCSV() → sendToQbBtn.click() 
  → fetch('/api/import-bills-csv')
```

---

## 📝 **VARIABILI GLOBALI JAVASCRIPT**

### **index.html**
```javascript
let lastExcelImportReport = null;  // Dati ultima importazione Excel
let performanceData = null;        // Metriche performance
```

### **token-status.js**  
```javascript
const tokenStatusElement = document.getElementById('token-status');
setInterval(checkTokenStatus, 300000); // Auto-refresh ogni 5 minuti
```

---

## 🎨 **CLASSI CSS DINAMICHE**

### **Status Visual**
- `.token-valid` - Token QB valido (verde)
- `.token-invalid` - Token QB scaduto (arancione) 
- `.token-error` - Errore token (rosso)
- `.selected-row` - Riga progetto selezionata
- `.badge-success/.badge-info/.badge-warning/.badge-secondary` - Status badge progetti

### **Performance Info**
- `#performanceInfo` - Barra informazioni performance (mostra/nascondi dinamico)
- `#performanceText` - Testo metriche velocità caricamento

---

## 🔧 **FILE JAVASCRIPT ESTERNI**

### **static/js/token-status.js**
- **Scopo**: Gestione stato token QuickBooks
- **Funzioni**: `checkTokenStatus()`, auto-refresh
- **DOM Target**: `#token-status` in header
- **Endpoint**: `/api/token-status`

---

Questa mappa dettagliata mostra ogni funzione JavaScript, i relativi elementi DOM, gli endpoint Flask collegati e i flussi operativi completi dell'applicazione AppConnettor.
