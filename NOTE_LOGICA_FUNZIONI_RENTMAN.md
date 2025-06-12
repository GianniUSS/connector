# Note su logica e funzioni per visualizzazione dati in grid web

## Logica generale per la grid
- Il modulo prepara i dati dei progetti Rentman in modo strutturato, ideale per la visualizzazione in una tabella/grid web.
- Ogni riga della grid rappresenta un progetto, con colonne per: ID, nome, stato, valore, periodo, tipo, cliente, responsabile, ecc.
- I dati sono normalizzati: lo status e il valore sono calcolati secondo la logica Rentman (vedi sotto), così la grid mostra sempre informazioni coerenti e affidabili.

## Calcolo dei campi principali per la grid
- **Valore progetto**: viene mostrato il valore del primo subproject per order (se esiste), altrimenti la somma dei subprojects, o infine il valore del progetto principale.
- **Status**: viene mostrato lo status del primo subproject con in_financial=True (se esiste), altrimenti lo status del progetto principale.
- **Periodo**: colonne per data inizio/fine (equipment_period_from, equipment_period_to).
- **Altri campi**: tipo progetto, nome cliente, responsabile, ecc.

## Funzioni chiave per la grid
- `list_projects_by_date_unified`: recupera e processa tutti i progetti in un intervallo di date, restituendo una lista di dict pronti per la grid.
- `filter_projects_by_status`: permette di filtrare la lista per mostrare solo i progetti con determinati stati (utile per filtri dinamici nella grid).
- Funzioni di supporto (`get_projecttype_name_cached`, `get_all_statuses`, ecc.) assicurano che i dati mostrati nella grid siano sempre “umani” (es. nomi invece di ID).

## Esempio di utilizzo per una grid web
```python
progetti = list_projects_by_date('2025-06-06', '2025-06-06')
stati_interesse = ["In location", "Rientrato", "Confermato", "Pronto"]
progetti_filtrati = filter_projects_by_status(progetti, stati_interesse)
# Ora puoi passare progetti_filtrati direttamente a una grid web (es. DataTable, ag-Grid, ecc.)
for p in progetti_filtrati:
    print(p)  # Ogni p è già un dict con tutti i campi per la grid
```

## Personalizzazione e flessibilità
- Puoi facilmente aggiungere/rimuovere colonne nella grid modificando la logica di `process_project`.
- Il filtro sugli stati è dinamico e può essere collegato a un filtro frontend.
- I dati sono già “puliti” e pronti per essere serializzati in JSON per API o frontend.
