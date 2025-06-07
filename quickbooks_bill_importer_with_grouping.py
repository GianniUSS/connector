"""
Estensione del QuickBooksBillImporter con supporto per il raggruppamento fatture.
"""

import logging
from typing import Dict, List, Optional, Any
from quickbooks_bill_importer import QuickBooksBillImporter
from bill_grouping_system import BillGroupingSystem, GroupedBill
import requests

class QuickBooksBillImporterWithGrouping(QuickBooksBillImporter):
    """
    Estensione del QuickBooksBillImporter che supporta il raggruppamento di fatture
    per fornitore in fatture multi-linea.
    """
    
    def __init__(self, base_url: str, realm_id: str, access_token: str):
        super().__init__(base_url, realm_id, access_token)
        self.grouping_system = BillGroupingSystem()
    
    def configure_grouping(self, rules: Dict[str, Any]):
        """
        Configura le regole di raggruppamento
        
        Args:
            rules: Dizionario con le regole di raggruppamento
        """
        self.grouping_system.set_grouping_rules(rules)
        logging.info(f"Regole di raggruppamento configurate: {rules}")
    
    def batch_import_bills_with_grouping(self, bills_list: List[Dict[str, Any]], 
                                       group_by_vendor: bool = True) -> Dict[str, Any]:
        """
        Importa fatture con opzione di raggruppamento per fornitore
        
        Args:
            bills_list: Lista delle fatture da importare
            group_by_vendor: Se True, raggruppa le fatture per fornitore
            
        Returns:
            Dizionario con i risultati dell'importazione
        """
        logging.info(f"[batch_import_with_grouping] Received {len(bills_list)} bills to import (group_by_vendor={group_by_vendor})")
        if not group_by_vendor:
            logging.info("[batch_import_with_grouping] Delegating to standard batch import")
            # Importazione standard senza raggruppamento
            return super().batch_import_bills(bills_list)
        
        # Importazione con raggruppamento
        return self._import_with_grouping(bills_list)
    
    def bill_exists(self, ref_number, vendor_id):
        """Controlla via QuickBooks se esiste già una fattura con stesso DocNumber e VendorRef"""
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        q = f"SELECT * FROM Bill WHERE DocNumber = '{ref_number}' AND VendorRef = '{vendor_id}'"
        params = {'query': q}
        resp = requests.get(url, headers=self.headers, params=params)
        if resp.status_code == 200:
            data = resp.json().get('QueryResponse', {})
            return bool(data.get('Bill'))
        return False

    def _import_with_grouping(self, bills_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Esegue l'importazione con raggruppamento delle fatture
        """
        from datetime import datetime
        def normalize_date(date_str):
            if not date_str:
                return date_str
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except Exception:
                    continue
            return date_str  # Se non riconosciuto, restituisce l'originale
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'skipped_count': 0,
            'grouped_count': 0,
            'original_bills_count': len(bills_list),
            'created_bills': [],
            'skipped_bills': [],
            'errors': [],
            'grouping_summary': {}
        }
        
        # Fase 1: Aggiungi tutte le fatture al sistema di raggruppamento
        logging.info("Fase 1: Raggruppamento fatture per fornitore...")
        logging.info(f"[import_with_grouping] Adding bills to grouping system")
        grouped_count = 0
        for bill_data in bills_list:
            logging.debug(f"[import_with_grouping] Adding bill: ref_number={bill_data.get('ref_number')} vendor_id={bill_data.get('vendor_id')}")
            if self.grouping_system.add_bill_for_grouping(bill_data):
                grouped_count += 1
            else:
                results['error_count'] += 1
                results['errors'].append(f"Errore raggruppamento fattura: {bill_data.get('ref_number', 'N/A')}")
        
        results['grouped_count'] = grouped_count
        
        # Fase 2: Ottieni le fatture raggruppate
        grouped_bills = self.grouping_system.get_grouped_bills()
        logging.info(f"Fase 2: Creazione di {len(grouped_bills)} fatture raggruppate in QuickBooks...")
        
        # Fase 3: Crea le fatture raggruppate in QuickBooks
        for i, grouped_bill in enumerate(grouped_bills):
            logging.info(f"[import_with_grouping] Creating grouped bill {i+1}/{len(grouped_bills)}: grouped_number={grouped_bill.grouped_bill_number} original_count={len(grouped_bill.original_bills)}")
            
            # Converti in formato QuickBooks
            bill_data = self.grouping_system.get_grouped_bill_data_for_qb(grouped_bill)
            
            # Normalizza le date nel payload
            if bill_data:
                if 'txn_date' in bill_data:
                    bill_data['txn_date'] = normalize_date(bill_data['txn_date'])
                if 'due_date' in bill_data:
                    bill_data['due_date'] = normalize_date(bill_data['due_date'])
            
            # Validazione approfondita del bill_data prima dell'invio
            if not bill_data:
                results['error_count'] += 1
                results['errors'].append(f"Errore generazione dati fattura raggruppata {grouped_bill.grouped_bill_number}")
                continue
                
            # Verifica campi obbligatori
            if not bill_data.get('vendor_id'):
                results['error_count'] += 1
                results['errors'].append(f"Errore fattura raggruppata {grouped_bill.grouped_bill_number}: Vendor ID mancante")
                continue
                
            if not bill_data.get('line_items') or len(bill_data.get('line_items', [])) == 0:
                results['error_count'] += 1
                results['errors'].append(f"Errore fattura raggruppata {grouped_bill.grouped_bill_number}: Line items mancanti")
                continue
                
            # Verifica importo totale
            if not bill_data.get('total_amount') or float(bill_data.get('total_amount', 0)) <= 0:
                results['error_count'] += 1
                results['errors'].append(f"Errore fattura raggruppata {grouped_bill.grouped_bill_number}: Importo totale non valido")
                continue
                
            # --- CONTROLLO IDEMPOTENZA: salta se già esiste ---
            ref_number = bill_data.get('ref_number')
            vendor_id = bill_data.get('vendor_id')
            if self.bill_exists(ref_number, vendor_id):
                results['skipped_count'] += 1
                results['skipped_bills'].append({'ref_number': ref_number, 'vendor_id': vendor_id})
                logging.info(f"Fattura raggruppata già esistente: {ref_number} (vendor {vendor_id}), saltata.")
                continue
                
            # Debug: log del payload prima dell'invio
            logging.info(f"Invio fattura raggruppata {grouped_bill.grouped_bill_number} con {len(bill_data.get('line_items', []))} righe")
                
            # Crea la fattura
            try:
                result = self.create_bill(bill_data)
                
                if result:
                    if result.get('skipped', False):
                        results['skipped_count'] += 1
                        results['skipped_bills'].append(result)
                        logging.info(f"Fattura raggruppata saltata: {grouped_bill.grouped_bill_number}")
                    elif result.get('error'):
                        results['error_count'] += 1
                        error_msg = result.get('error', 'Errore sconosciuto')
                        status_code = result.get('status_code', 'N/A')
                        results['errors'].append(f"Errore fattura raggruppata {grouped_bill.grouped_bill_number}: {error_msg} (Status: {status_code})")
                    else:
                        results['success_count'] += 1
                        results['created_bills'].append(result)
                        logging.info(f"Fattura raggruppata creata con successo: {grouped_bill.grouped_bill_number}")
                else:
                    results['error_count'] += 1
                    results['errors'].append(f"Errore fattura raggruppata {grouped_bill.grouped_bill_number}: Nessun risultato")
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append(f"Eccezione durante creazione fattura raggruppata {grouped_bill.grouped_bill_number}: {str(e)}")
                logging.error(f"Eccezione durante creazione fattura raggruppata: {str(e)}")
        
        # Aggiungi il riepilogo del raggruppamento
        results['grouping_summary'] = self.grouping_system.get_grouping_summary()
        
        logging.info(f"Importazione con raggruppamento completata. "
                    f"Successi: {results['success_count']}, "
                    f"Saltate: {results['skipped_count']}, "
                    f"Errori: {results['error_count']}")
        logging.info(f"[import_with_grouping] Completed grouped import: success={results['success_count']} errors={results['error_count']} skipped={results['skipped_count']}")
        
        return results
    
    def preview_grouping(self, bills_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Anteprima del raggruppamento senza creare fatture in QuickBooks
        
        Args:
            bills_list: Lista delle fatture da raggruppare
            
        Returns:
            Dizionario con l'anteprima del raggruppamento
        """
        # Pulisci i gruppi esistenti
        self.grouping_system.clear_groups()
        
        # Aggiungi le fatture al sistema di raggruppamento
        for bill_data in bills_list:
            self.grouping_system.add_bill_for_grouping(bill_data)
        
        # Restituisci il riepilogo
        summary = self.grouping_system.get_grouping_summary()
        
        # Aggiungi dettagli delle fatture raggruppate
        grouped_bills = self.grouping_system.get_grouped_bills()
        detailed_groups = []
        
        for grouped_bill in grouped_bills:
            group_detail = {
                'grouped_bill_number': grouped_bill.grouped_bill_number,
                'vendor_name': grouped_bill.vendor_name,
                'vendor_id': grouped_bill.vendor_id,
                'total_amount': grouped_bill.total_amount,
                'txn_date': grouped_bill.txn_date,
                'due_date': grouped_bill.due_date,
                'original_bills': grouped_bill.original_bills,
                'line_items_count': len(grouped_bill.line_items),
                'memo': grouped_bill.memo,
                'line_items': [
                    {
                        'amount': item.amount,
                        'description': item.description,
                        'account_id': item.account_id,
                        'original_bill': item.original_bill_number
                    }
                    for item in grouped_bill.line_items
                ]
            }
            detailed_groups.append(group_detail)
        
        summary['detailed_groups'] = detailed_groups
        return summary
    
    def get_grouping_statistics(self) -> Dict[str, Any]:
        """
        Restituisce statistiche dettagliate sul raggruppamento corrente
        """
        summary = self.grouping_system.get_grouping_summary()
        
        # Aggiungi statistiche aggiuntive
        if summary['total_groups'] > 0:
            avg_bills_per_group = summary['total_original_bills'] / summary['total_groups']
            avg_amount_per_group = summary['total_amount'] / summary['total_groups']
            
            # Trova il gruppo con più fatture
            max_bills_group = max(summary['groups'], key=lambda x: x['original_bills_count'])
            # Trova il gruppo con importo maggiore
            max_amount_group = max(summary['groups'], key=lambda x: x['total_amount'])
            
            summary['statistics'] = {
                'avg_bills_per_group': round(avg_bills_per_group, 2),
                'avg_amount_per_group': round(avg_amount_per_group, 2),
                'max_bills_in_group': max_bills_group['original_bills_count'],
                'max_bills_group_vendor': max_bills_group['vendor_name'],
                'max_amount_in_group': max_amount_group['total_amount'],
                'max_amount_group_vendor': max_amount_group['vendor_name']
            }
        
        return summary
    
    def export_grouping_preview(self, bills_list: List[Dict[str, Any]], 
                              file_path: str) -> bool:
        """
        Esporta un'anteprima del raggruppamento in un file JSON
        
        Args:
            bills_list: Lista delle fatture da raggruppare
            file_path: Percorso del file di output
            
        Returns:
            True se l'esportazione è riuscita, False altrimenti
        """
        try:
            preview = self.preview_grouping(bills_list)
            
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(preview, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Anteprima raggruppamento esportata in: {file_path}")
            return True
            
        except Exception as e:
            logging.error(f"Errore nell'esportazione dell'anteprima: {e}")
            return False
    
    def reset_grouping(self):
        """Resetta il sistema di raggruppamento"""
        self.grouping_system.clear_groups()
        logging.info("Sistema di raggruppamento resettato")


# Utility per testing
def test_grouping_system():
    """Funzione di test per il sistema di raggruppamento"""
    # Dati di test
    test_bills = [
        {
            'vendor_id': '1001',
            'vendor_name': 'Enel Energia',
            'ref_number': 'EE001',
            'txn_date': '2024-01-15',
            'due_date': '2024-02-15',
            'line_items': [
                {'amount': 120.50, 'description': 'Energia elettrica Gennaio', 'account_id': '1'},
            ]
        },
        {
            'vendor_id': '1001',  # Stesso fornitore
            'vendor_name': 'Enel Energia',
            'ref_number': 'EE002',
            'txn_date': '2024-01-20',
            'due_date': '2024-02-20',
            'line_items': [
                {'amount': 95.30, 'description': 'Energia elettrica conguaglio', 'account_id': '1'},
            ]
        },
        {
            'vendor_id': '1002',  # Fornitore diverso
            'vendor_name': 'Telecom Italia',
            'ref_number': 'TI001',
            'txn_date': '2024-01-16',
            'due_date': '2024-02-16',
            'line_items': [
                {'amount': 45.00, 'description': 'Telefonia fissa', 'account_id': '2'},
                {'amount': 15.00, 'description': 'Internet ADSL', 'account_id': '2'},
            ]
        },
        {
            'vendor_id': '1001',  # Altro Enel
            'vendor_name': 'Enel Energia',
            'ref_number': 'EE003',
            'txn_date': '2024-01-25',
            'due_date': '2024-02-25',
            'line_items': [
                {'amount': 78.20, 'description': 'Energia elettrica uffici', 'account_id': '1'},
            ]
        }
    ]
    
    # Crea l'importer con raggruppamento (usando token di test)
    importer = QuickBooksBillImporterWithGrouping(
        base_url="https://sandbox-quickbooks.api.intuit.com",
        realm_id="test_realm",
        access_token="test_token"
    )
    
    # Configura le regole di raggruppamento
    importer.configure_grouping({
        'by_vendor': True,
        'merge_same_account': True,
        'max_lines_per_bill': 50
    })
    
    # Anteprima del raggruppamento
    print("=== ANTEPRIMA RAGGRUPPAMENTO ===")
    preview = importer.preview_grouping(test_bills)
    
    print(f"Fatture originali: {preview['total_original_bills']}")
    print(f"Gruppi creati: {preview['total_groups']}")
    print(f"Importo totale: €{preview['total_amount']:.2f}")
    
    print("\nDettaglio gruppi:")
    for group in preview['detailed_groups']:
        print(f"\n- {group['grouped_bill_number']} ({group['vendor_name']})")
        print(f"  Fatture originali: {', '.join(group['original_bills'])}")
        print(f"  Righe: {group['line_items_count']}, Totale: €{group['total_amount']:.2f}")
        print(f"  Memo: {group['memo'][:100]}...")
    
    # Esporta l'anteprima
    if importer.export_grouping_preview(test_bills, "anteprima_raggruppamento.json"):
        print("\n✅ Anteprima esportata in 'anteprima_raggruppamento.json'")
    
    return preview


if __name__ == "__main__":
    # Configura logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Esegui il test
    test_grouping_system()
