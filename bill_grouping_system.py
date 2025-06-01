"""
Sistema di raggruppamento fatture per QuickBooks Bill Importer.
Consente di raggruppare più fatture dello stesso fornitore in una singola fattura multi-linea.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json

@dataclass
class BillLineItem:
    """Rappresenta una riga di fattura"""
    amount: float
    description: str
    account_id: str = "1"
    taxcode_id: Optional[str] = None
    original_bill_number: Optional[str] = None
    original_bill_date: Optional[str] = None

@dataclass
class GroupedBill:
    """Rappresenta una fattura raggruppata"""
    vendor_id: str
    vendor_name: str
    line_items: List[BillLineItem]
    total_amount: float
    grouped_bill_number: str
    txn_date: str
    due_date: Optional[str] = None
    memo: Optional[str] = None
    original_bills: List[str] = None  # Lista dei numeri fattura originali
    
    def __post_init__(self):
        if self.original_bills is None:
            self.original_bills = []

class BillGroupingSystem:
    """
    Sistema per raggruppare fatture per fornitore e creare fatture multi-linea
    """
    
    def __init__(self):
        self.grouped_bills: Dict[str, GroupedBill] = {}
        self.grouping_rules = {            'by_vendor': True,           # Raggruppa per fornitore
            'by_date': False,            # Raggruppa per data (opzionale)
            'date_tolerance_days': 7,    # Tolleranza in giorni per il raggruppamento per data
            'max_lines_per_bill': 50,    # Numero massimo di righe per fattura
            'merge_same_account': True,  # Unisci righe dello stesso account
            'by_invoice_and_vendor': True # NUOVA REGOLA: raggruppa per Numero Fattura + Fornitore
        }
    
    def set_grouping_rules(self, rules: Dict[str, Any]):
        """Configura le regole di raggruppamento"""
        self.grouping_rules.update(rules)
        logging.info(f"Regole di raggruppamento aggiornate: {self.grouping_rules}")
    
    def add_bill_for_grouping(self, bill_data: Dict[str, Any]) -> bool:
        """
        Aggiunge una fattura al sistema di raggruppamento
        
        Args:
            bill_data: Dati della fattura da aggiungere
            
        Returns:
            bool: True se aggiunta con successo, False altrimenti
        """
        try:
            vendor_id = bill_data.get('vendor_id')
            vendor_name = bill_data.get('vendor_name', f'Fornitore_{vendor_id}')
            ref_number = bill_data.get('ref_number', 'N/A')
            txn_date = bill_data.get('txn_date', datetime.now().strftime('%Y-%m-%d'))
            
            if not vendor_id:
                logging.error("vendor_id mancante nei dati fattura")
                return False
            
            # Crea le righe dalla fattura originale
            line_items = []
            for item in bill_data.get('line_items', []):
                line_item = BillLineItem(
                    amount=float(item.get('amount', 0)),
                    description=item.get('description', f'Fattura {ref_number}'),
                    account_id=item.get('account_id', '1'),
                    taxcode_id=item.get('taxcode_id'),
                    original_bill_number=ref_number,
                    original_bill_date=txn_date
                )
                line_items.append(line_item)
            
            # Determina la chiave di raggruppamento
            group_key = self._get_group_key(vendor_id, ref_number, txn_date)
            
            if group_key in self.grouped_bills:
                # Aggiungi alla fattura raggruppata esistente
                self._add_to_existing_group(group_key, line_items, ref_number)
            else:
                # Crea una nuova fattura raggruppata
                self._create_new_group(group_key, vendor_id, vendor_name, line_items, 
                                     ref_number, txn_date, bill_data)
            
            logging.info(f"Fattura {ref_number} aggiunta al gruppo {group_key}")
            return True
            
        except Exception as e:
            logging.error(f"Errore nell'aggiunta della fattura al raggruppamento: {e}")
            return False
    
    def _get_group_key(self, vendor_id: str, ref_number: str, txn_date: str) -> str:
        """Determina la chiave di raggruppamento basata sulle regole configurate"""
        if self.grouping_rules.get('by_invoice_and_vendor', False):
            # Raggruppa per fornitore + numero fattura
            return f"{vendor_id}__{ref_number}"
        elif self.grouping_rules.get('by_date', False):
            # Raggruppa per fornitore e settimana
            try:
                date_obj = datetime.strptime(txn_date, '%Y-%m-%d')
                week_num = date_obj.isocalendar()[1]
                year = date_obj.year
                return f"{vendor_id}_{year}_W{week_num}"
            except:
                return f"{vendor_id}_date_invalid"
        else:
            # Raggruppa solo per fornitore
            return f"{vendor_id}"
    
    def _add_to_existing_group(self, group_key: str, line_items: List[BillLineItem], 
                             ref_number: str):
        """Aggiunge righe a un gruppo esistente"""
        grouped_bill = self.grouped_bills[group_key]
        
        # Controlla il limite di righe
        if (len(grouped_bill.line_items) + len(line_items) > 
            self.grouping_rules.get('max_lines_per_bill', 50)):
            logging.warning(f"Limite righe superato per gruppo {group_key}, "
                          f"creazione gruppo separato necessaria")
            # In futuro: creare un secondo gruppo
            return
        
        # Aggiungi le righe
        if self.grouping_rules.get('merge_same_account', True):
            self._merge_lines_by_account(grouped_bill, line_items)
        else:
            grouped_bill.line_items.extend(line_items)
        
        # Aggiorna il totale
        grouped_bill.total_amount = sum(item.amount for item in grouped_bill.line_items)
        
        # Aggiorna la lista delle fatture originali
        if ref_number not in grouped_bill.original_bills:
            grouped_bill.original_bills.append(ref_number)
        
        # Aggiorna la descrizione del memo
        grouped_bill.memo = self._generate_group_memo(grouped_bill)
    
    def _merge_lines_by_account(self, grouped_bill: GroupedBill, 
                               new_line_items: List[BillLineItem]):
        """Unisce le righe dello stesso account per ridurre il numero di righe"""
        # Crea un dizionario per account esistenti
        existing_accounts = {}
        for i, item in enumerate(grouped_bill.line_items):
            key = f"{item.account_id}_{item.taxcode_id or 'no_tax'}"
            if key not in existing_accounts:
                existing_accounts[key] = i
        
        # Processa le nuove righe
        for new_item in new_line_items:
            key = f"{new_item.account_id}_{new_item.taxcode_id or 'no_tax'}"
            
            if key in existing_accounts:
                # Unisci con la riga esistente
                existing_index = existing_accounts[key]
                existing_item = grouped_bill.line_items[existing_index]
                existing_item.amount += new_item.amount
                # Aggiorna la descrizione per includere entrambe le fatture
                if new_item.original_bill_number:
                    existing_item.description += f", {new_item.original_bill_number}"
            else:
                # Aggiungi come nuova riga
                grouped_bill.line_items.append(new_item)
                existing_accounts[key] = len(grouped_bill.line_items) - 1
    
    def _create_new_group(self, group_key: str, vendor_id: str, vendor_name: str,
                         line_items: List[BillLineItem], ref_number: str, 
                         txn_date: str, bill_data: Dict[str, Any]):
        """Crea un nuovo gruppo di fatture"""
        total_amount = sum(item.amount for item in line_items)
        
        # Usa il numero della fattura originale come numero della fattura raggruppata
        grouped_bill_number = self._generate_grouped_bill_number(vendor_name, txn_date, ref_number)
        
        grouped_bill = GroupedBill(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            line_items=line_items,
            total_amount=total_amount,
            grouped_bill_number=grouped_bill_number,
            txn_date=txn_date,
            due_date=bill_data.get('due_date'),
            original_bills=[ref_number]
        )
        
        grouped_bill.memo = self._generate_group_memo(grouped_bill)
        self.grouped_bills[group_key] = grouped_bill
    
    def _generate_grouped_bill_number(self, vendor_name: str, txn_date: str, ref_number: str = None) -> str:
        """Restituisce il numero della fattura originale come numero della fattura raggruppata"""
        if ref_number:
            return str(ref_number)
        # fallback: se non c'è ref_number, usa la vecchia logica
        try:
            date_obj = datetime.strptime(txn_date, '%Y-%m-%d')
            date_str = date_obj.strftime('%Y%m%d')
        except:
            date_str = datetime.now().strftime('%Y%m%d')
        vendor_prefix = ''.join(c for c in vendor_name if c.isalpha())[:3].upper()
        if not vendor_prefix:
            vendor_prefix = 'GRP'
        return f"GRP_{vendor_prefix}_{date_str}"
    
    def _generate_group_memo(self, grouped_bill: GroupedBill) -> str:
        """Genera il memo per la fattura raggruppata"""
        original_count = len(grouped_bill.original_bills)
        bills_list = ', '.join(grouped_bill.original_bills[:5])  # Prime 5 fatture        
        if original_count > 5:
            bills_list += f" (+{original_count - 5} altre)"
        
        return (f"Fattura raggruppata da {original_count} fatture originali: {bills_list}. "
                f"Totale: €{grouped_bill.total_amount:.2f}")
    
    def get_grouped_bills(self) -> List[GroupedBill]:
        """Restituisce tutte le fatture raggruppate"""
        return list(self.grouped_bills.values())
    def get_grouped_bill_data_for_qb(self, grouped_bill: GroupedBill) -> Dict[str, Any]:
        """
        Converte una fattura raggruppata nel formato richiesto da QuickBooksBillImporter
        Accetta solo i campi previsti dalla documentazione QuickBooks e rimuove ogni campo custom/non previsto.
        """
        logging.info(f"[get_grouped_bill_data_for_qb] Creazione payload per fattura raggruppata: {grouped_bill.grouped_bill_number}")

        # Costruisci le linee solo con i campi previsti
        line_items = []
        for item in grouped_bill.line_items:
            line_item = {
                'amount': float(item.amount),
                'description': str(item.description) if item.description else "",
                'account_id': str(item.account_id) if item.account_id else "1"
            }
            # Solo se presente, aggiungi taxcode_id
            if item.taxcode_id:
                line_item['taxcode_id'] = str(item.taxcode_id)
            # Non aggiungere altri campi (es. original_bill_number, original_bill_date, ecc.)
            line_items.append(line_item)

        # Costruisci il dizionario solo con i campi previsti
        bill_data = {
            'vendor_id': str(grouped_bill.vendor_id),
            'txn_date': str(grouped_bill.txn_date) if grouped_bill.txn_date else datetime.now().strftime('%Y-%m-%d'),
            'line_items': line_items,
            'total_amount': float(grouped_bill.total_amount)
        }
        # Campi opzionali solo se previsti e non vuoti
        if grouped_bill.due_date and grouped_bill.due_date.strip():
            bill_data['due_date'] = str(grouped_bill.due_date)
        if grouped_bill.grouped_bill_number and grouped_bill.grouped_bill_number.strip():
            bill_data['ref_number'] = str(grouped_bill.grouped_bill_number)
        if grouped_bill.memo and grouped_bill.memo.strip():
            bill_data['memo'] = str(grouped_bill.memo)
        # Taxcode a livello fattura solo se presente
        tax_code_items = [item for item in grouped_bill.line_items if item.taxcode_id]
        if tax_code_items:
            bill_data['taxcode_id'] = str(tax_code_items[0].taxcode_id)

        # AVVISO: Non aggiungere altri campi custom o non previsti dal payload QuickBooks
        logging.info(f"[get_grouped_bill_data_for_qb] Payload creato con {len(line_items)} righe, totale: {bill_data['total_amount']}")
        return bill_data
    
    def clear_groups(self):
        """Pulisce tutti i gruppi"""
        self.grouped_bills.clear()
        logging.info("Tutti i gruppi sono stati cancellati")
    
    def get_grouping_summary(self) -> Dict[str, Any]:
        """Restituisce un riepilogo del raggruppamento"""
        total_groups = len(self.grouped_bills)
        total_original_bills = sum(len(group.original_bills) for group in self.grouped_bills.values())
        total_amount = sum(group.total_amount for group in self.grouped_bills.values())
        
        groups_info = []
        for group_key, group in self.grouped_bills.items():
            groups_info.append({
                'group_key': group_key,
                'vendor_name': group.vendor_name,
                'original_bills_count': len(group.original_bills),
                'lines_count': len(group.line_items),
                'total_amount': group.total_amount,
                'grouped_bill_number': group.grouped_bill_number
            })
        
        return {
            'total_groups': total_groups,
            'total_original_bills': total_original_bills,
            'total_amount': total_amount,
            'groups': groups_info,
            'grouping_rules': self.grouping_rules
        }
    
    def export_groups_to_json(self, file_path: str) -> bool:
        """Esporta i gruppi in un file JSON"""
        try:
            summary = self.get_grouping_summary()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logging.info(f"Gruppi esportati in {file_path}")
            return True
        except Exception as e:
            logging.error(f"Errore nell'esportazione dei gruppi: {e}")
            return False
    
    def group_bills(self, df, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Metodo wrapper per processare un DataFrame di fatture e restituire i gruppi
        
        Args:
            df: DataFrame con le fatture
            config: Configurazione del raggruppamento
            
        Returns:
            Lista di dizionari rappresentanti le fatture raggruppate
        """
        # Applica la configurazione
        self.set_grouping_rules({
            'by_vendor': config.get('group_by_vendor', True),
            'by_date': False,
            'max_lines_per_bill': config.get('max_lines_per_bill', 50)
        })
        
        # Pulisci i gruppi esistenti
        self.clear_groups()
        
        # Processa ogni riga del DataFrame
        for _, row in df.iterrows():
            bill_data = {
                'vendor_id': str(hash(row['Vendor'])),  # Genero un ID dal nome
                'vendor_name': row['Vendor'],
                'bill_number': row['Bill No.'],
                'txn_date': row['Date'],
                'total_amount': float(row['Bill Total']),
                'line_items': [{
                    'amount': float(row['Line Item Amount']),
                    'description': row['Line Item Description'],
                    'account_id': row['Line Item Account']
                }]
            }
            
            self.add_bill_for_grouping(bill_data)
        
        # Ottieni i gruppi e convertili in formato compatibile
        grouped_bills = self.get_grouped_bills()
        result = []
        
        for grouped_bill in grouped_bills:
            # Unisci le righe dello stesso account se richiesto
            if config.get('merge_same_accounts', True):
                self._merge_lines_by_account_simple(grouped_bill)
            
            bill_dict = {
                'bill_no': grouped_bill.grouped_bill_number,
                'vendor': grouped_bill.vendor_name,
                'total': grouped_bill.total_amount,
                'date': grouped_bill.txn_date,
                'memo': self._generate_group_memo(grouped_bill),
                'original_bills': grouped_bill.original_bills,
                'line_items': []
            }
            
            for line_item in grouped_bill.line_items:
                bill_dict['line_items'].append({
                    'account': line_item.account_id,
                    'description': line_item.description,
                    'amount': line_item.amount
                })
            
            result.append(bill_dict)
        
        return result
    
    def _merge_lines_by_account_simple(self, grouped_bill: GroupedBill):
        """Versione semplificata per unire righe dello stesso account"""
        account_map = {}
        
        for line in grouped_bill.line_items:
            account_key = line.account_id
            if account_key in account_map:
                # Unisci con la riga esistente
                existing_line = account_map[account_key]
                existing_line.amount += line.amount
                if line.description not in existing_line.description:
                    existing_line.description += f"; {line.description}"
            else:
                account_map[account_key] = line
        
        # Sostituisci le righe con quelle unite
        grouped_bill.line_items = list(account_map.values())
    
    def get_grouping_statistics(self, original_df, grouped_bills: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Restituisce statistiche dettagliate sul raggruppamento
        """
        original_bills_count = original_df['Bill No.'].nunique()
        original_vendors = original_df['Vendor'].unique()
        original_total = original_df['Line Item Amount'].sum()
        
        grouped_bills_count = len(grouped_bills)
        grouped_total = sum(bill['total'] for bill in grouped_bills)
        
        # Statistiche per fornitore
        vendor_stats = {}
        for vendor in original_vendors:
            vendor_df = original_df[original_df['Vendor'] == vendor]
            original_count = vendor_df['Bill No.'].nunique()
            
            grouped_count = len([bill for bill in grouped_bills if bill['vendor'] == vendor])
            
            vendor_stats[vendor] = {
                'fatture_originali': original_count,
                'fatture_raggruppate': grouped_count,
                'riduzione': original_count - grouped_count,
                'percentuale_riduzione': ((original_count - grouped_count) / original_count * 100) if original_count > 0 else 0
            }
        
        return {
            'fatture_originali': original_bills_count,
            'fatture_raggruppate': grouped_bills_count,
            'riduzione_totale': original_bills_count - grouped_bills_count,
            'percentuale_riduzione_totale': ((original_bills_count - grouped_bills_count) / original_bills_count * 100) if original_bills_count > 0 else 0,
            'totale_originale': float(original_total),
            'totale_raggruppato': float(grouped_total),
            'fornitori_processati': len(original_vendors),
            'dettagli_fornitori': vendor_stats
        }

# Funzione di test per il sistema di raggruppamento
def test_grouped_bill_creation():
    """
    Funzione di test per verificare la creazione di una fattura raggruppata in QuickBooks.
    Questo test verifica che il payload generato per le fatture raggruppate sia valido.
    """
    from quickbooks_bill_importer_with_grouping import QuickBooksBillImporterWithGrouping
    import os
    import json
    
    # Configura logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Impostazioni da variabili d'ambiente o valori di default per test
    qb_base_url = os.environ.get('QB_BASE_URL', 'https://sandbox-quickbooks.api.intuit.com')
    qb_realm_id = os.environ.get('QB_REALM_ID', 'test_realm')
    qb_token = os.environ.get('QB_TOKEN', 'test_token')
    
    # Crea l'importer con supporto al raggruppamento
    importer = QuickBooksBillImporterWithGrouping(
        base_url=qb_base_url,
        realm_id=qb_realm_id,
        access_token=qb_token
    )
    
    # Configura le regole di raggruppamento
    importer.configure_grouping({
        'by_vendor': True,
        'merge_same_account': True,
        'max_lines_per_bill': 10
    })
    
    # Crea alcune fatture di esempio con lo stesso fornitore
    test_bills = [
        {
            'vendor_id': '56',  # Usa un ID fornitore valido dal tuo QuickBooks
            'vendor_name': 'Fornitore Test',
            'ref_number': 'TEST001',
            'txn_date': '2024-05-01',
            'due_date': '2024-06-01',
            'line_items': [
                {
                    'amount': 100.00,
                    'description': 'Articolo test 1',
                    'account_id': '54'  # Usa un ID conto valido dal tuo QuickBooks
                }
            ],
            'total_amount': 100.00
        },
        {
            'vendor_id': '56',  # Stesso fornitore
            'vendor_name': 'Fornitore Test',
            'ref_number': 'TEST002',
            'txn_date': '2024-05-02',
            'due_date': '2024-06-02',
            'line_items': [
                {
                    'amount': 200.00,
                    'description': 'Articolo test 2',
                    'account_id': '54'  # Stesso conto per testare il merge
                }
            ],
            'total_amount': 200.00
        }
    ]
    
    # Esporta le fatture di test in un file per riferimento
    with open("test_bills.json", "w", encoding="utf-8") as f:
        json.dump(test_bills, f, indent=2, ensure_ascii=False)
    
    print("=" * 80)
    print("TEST CREAZIONE FATTURA RAGGRUPPATA")
    print("=" * 80)
    
    # Testa il raggruppamento e la creazione
    result = importer.batch_import_bills_with_grouping(test_bills, group_by_vendor=True)
    
    # Stampa il risultato
    print("\nRISULTATO:")
    print(f"Successi: {result['success_count']}")
    print(f"Errori: {result['error_count']}")
    print(f"Saltate: {result['skipped_count']}")
    
    if result['errors']:
        print("\nERRORI:")
        for error in result['errors']:
            print(f"- {error}")
    
    # Salva il risultato per analisi
    with open("test_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str, ensure_ascii=False)
    
    print("\nTest completato. Risultato salvato in 'test_result.json'")
    return result

# Esempio di utilizzo
if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(level=logging.INFO)
    
    # Crea il sistema di raggruppamento
    grouping_system = BillGroupingSystem()
    
    # Configura regole (opzionale)
    grouping_system.set_grouping_rules({
        'by_vendor': True,
        'merge_same_account': True,
        'max_lines_per_bill': 25
    })
    
    # Esempio fatture da raggruppare
    sample_bills = [
        {
            'vendor_id': '1001',
            'vendor_name': 'Fornitore A',
            'ref_number': 'FATT001',
            'txn_date': '2024-01-15',
            'due_date': '2024-02-15',
            'line_items': [
                {'amount': 100.0, 'description': 'Servizio 1', 'account_id': '1'},
                {'amount': 50.0, 'description': 'Servizio 2', 'account_id': '2'}
            ]
        },
        {
            'vendor_id': '1001',  # Stesso fornitore
            'vendor_name': 'Fornitore A',
            'ref_number': 'FATT002',
            'txn_date': '2024-01-16',
            'due_date': '2024-02-16',
            'line_items': [
                {'amount': 75.0, 'description': 'Servizio 3', 'account_id': '1'},
                {'amount': 25.0, 'description': 'Servizio 4', 'account_id': '3'}
            ]
        }
    ]
    
    # Aggiungi le fatture al sistema
    for bill in sample_bills:
        grouping_system.add_bill_for_grouping(bill)
    
    # Ottieni il riepilogo
    summary = grouping_system.get_grouping_summary()
    print("Riepilogo raggruppamento:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
