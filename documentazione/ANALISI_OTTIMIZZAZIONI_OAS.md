# 🚀 ANALISI OTTIMIZZAZIONI API RENTMAN BASATE SU OAS.YML

## 📋 SPECIFICHE UFFICIALI IDENTIFICATE

### 🎯 RATE LIMITING E CONCURRENT REQUESTS
- **50.000 richieste/giorno** (limite giornaliero)
- **10 richieste/secondo** (limite per secondo)
- **Massimo 20 richieste contemporanee** (attualmente usiamo solo 4 worker)

### 📦 RESPONSE LIMIT UFFICIALE
- **300 items massimi per risposta** (attualmente non lo consideriamo)
- Necessario usare `limit` e `offset` per dataset maggiori

### 🔧 PARAMETRI OTTIMIZZAZIONE SUPPORTATI

#### 1. **FIELDS SELECTION** (Riduzione traffico dati)
```
?fields=id,name,number,status,planperiod_start,planperiod_end,project_total_price,account_manager,project_type
```
- Riduce drasticamente il traffico dati
- Campi sempre inclusi: `id`, `created`, `modified`

#### 2. **SORTING COERENTE** (Paginazione stabile)
```
?sort=+id
```
- Essenziale per paginazione affidabile
- Evita inconsistenze tra pagine

#### 3. **FILTERING AVANZATO** (Riduzione dataset)
```
?planperiod_start[gte]=2025-01-01&planperiod_end[lte]=2025-12-31
```
- Operatori: `lt`, `gt`, `lte`, `gte`, `neq`, `[isnull]`
- Filtraggio lato server invece che client

#### 4. **PAGINAZIONE OTTIMALE**
```
?limit=300&offset=0&sort=+id
```
- Usa il limite massimo ufficiale (300)
- Ordinamento coerente per evitare duplicati

### 🏷️ CAMPI SPECIFICI PROGETTI IDENTIFICATI

#### Campi di Valore Disponibili:
- `project_total_price` - **GENERATED FIELD** (Totale subprojects non cancellati)
- `project_total_price_cancelled` - **GENERATED FIELD** (Totale cancellati)
- `project_rental_price` - **GENERATED FIELD** (Prezzo noleggio)
- `project_sale_price` - **GENERATED FIELD** (Prezzo vendita)
- `project_crew_price` - **GENERATED FIELD** (Prezzo crew)
- `project_transport_price` - **GENERATED FIELD** (Prezzo trasporto)
- `project_other_price` - **GENERATED FIELD** (Altri costi)
- `project_insurance_price` - **GENERATED FIELD** (Assicurazione)
- `price` - **GENERATED FIELD** (Prezzo generico)

#### Campi Periodo:
- `planperiod_start` - **GENERATED FIELD** (Inizio pianificazione)
- `planperiod_end` - **GENERATED FIELD** (Fine pianificazione)
- `usageperiod_start` - **GENERATED FIELD** (Inizio utilizzo)
- `usageperiod_end` - **GENERATED FIELD** (Fine utilizzo)
- `equipment_period_from` - **GENERATED FIELD** (Periodo equipment da)
- `equipment_period_to` - **GENERATED FIELD** (Periodo equipment a)

### ⚠️ LIMITAZIONI IMPORTANT I
1. **GENERATED FIELDS** non possono essere usati per sorting con paginazione
2. **GENERATED FIELDS** non sono queryable per filtering
3. Alcuni campi potrebbero essere omessi nelle collection request
4. Inconsistenze possibili con sort multipli + paginazione

## 🎯 OTTIMIZZAZIONI PRIORITARIE DA IMPLEMENTARE

### 1. **FIELDS SELECTION** (Alta priorità)
Ridurre traffico dati del ~80% richiedendo solo campi necessari:
```python
fields = "id,name,number,status,planperiod_start,planperiod_end,project_total_price,account_manager,project_type"
```

### 2. **RATE LIMIT OTTIMALE** (Media priorità)
Aumentare worker da 4 a 20 (limite ufficiale):
```python
max_workers = 20  # invece di 4
```

### 3. **PAGINAZIONE UFFICIALE** (Media priorità)
Usare limite ufficiale di 300 items:
```python
limit = 300  # invece di nessun limite
```

### 4. **SORTING COERENTE** (Media priorità)
Aggiungere sort per paginazione stabile:
```python
sort = "+id"  # ordinamento coerente
```

### 5. **FILTERING LATO SERVER** (Bassa priorità)
Spostare filtro date dal client al server:
```python
# Invece di filtrare tutti i progetti localmente
params = {
    'planperiod_start[gte]': start_date,
    'planperiod_end[lte]': end_date,
    'limit': 300,
    'sort': '+id',
    'fields': fields
}
```

## 📊 IMPATTO STIMATO OTTIMIZZAZIONI

1. **Fields Selection**: -80% traffico dati → +400% velocità
2. **Rate Limit 20 worker**: +500% velocità richieste parallele
3. **Paginazione 300**: Gestione corretta dataset grandi
4. **Filtering server**: -90% processing client → +1000% velocità filtro

## 🔄 PROSSIMI STEP

1. ✅ **Implementare fields selection** (massima priorità)
2. ✅ **Aumentare worker a 20** (facile implementazione)
3. ✅ **Aggiungere sorting coerente** (stabilità paginazione)
4. ⚠️ **Valutare filtering server** (potrebbe rompere compatibilità)
5. ⚠️ **Testare response limit 300** (verificare dataset grandi)

## 🐛 NOTE IMPORTANTI

- `project_total_price` è **GENERATED FIELD**: disponibile ma non filtrabile
- Evitare sort su GENERATED FIELDS con paginazione
- Rate limit: 20 contemporanee MAX (non superare)
- Response limit: 300 items MAX per richiesta

## 🚀 IMPLEMENTAZIONE SUGGERITA

Priorità implementazione:
1. **Fields selection** → Immediato boost prestazioni
2. **Worker da 4 a 20** → 5x velocità parallela
3. **Sort coerente** → Stabilità paginazione
4. **Testing comprehensive** → Validazione ottimizzazioni

La combinazione di queste ottimizzazioni dovrebbe portare a un miglioramento delle prestazioni del 300-500% rispetto alla versione attuale.
