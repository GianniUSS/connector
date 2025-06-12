#!/usr/bin/env python
# -*- coding: utf-8 -*-
# preview_bill_payload.py - Visualizza anteprima del payload fattura fornitore

import json
import argparse
from quickbooks_bill_importer import QuickBooksBillImporter
from typing import Dict, Any, List

def create_sample_bill_data() -> Dict[str, Any]:
    """Crea un esempio di dati di fattura per test"""
    return {
        'vendor_id': '123',  # ID QuickBooks del fornitore
        'txn_date': '2025-05-30',  # Data della transazione
        'due_date': '2025-06-30',  # Data di scadenza
        'ref_number': 'FATT-001',  # Numero di riferimento fattura
        'memo': 'Fattura di esempio',  # Memo/note
        'taxcode_id': '2',  # ID codice fiscale QuickBooks
        'line_items': [
            {
                'amount': 100.00,
                'description': 'Servizio A',
                'account_id': '54',  # Conto spese
                'taxcode_id': '2'
            },
            {
                'amount': 200.00,
                'description': 'Servizio B',
                'account_id': '55',
                'taxcode_id': '2'
            },
            {
                'amount': 300.00,
                'description': 'Articolo C',
                'item_id': '22',  # Se si usa item invece di account
                'quantity': 2,
                'unit_price': 150.00,
                'taxcode_id': '2'
            }
        ],
        'total_amount': 600.00  # Totale della fattura
    }

def load_bill_data_from_file(filepath: str) -> Dict[str, Any]:
    """Carica i dati della fattura da un file JSON"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento del file {filepath}: {e}")
        return create_sample_bill_data()

def preview_bill_payload(bill_data: Dict[str, Any], output_file: str = None) -> None:
    """
    Genera un'anteprima del payload QuickBooks per la fattura senza inviarla
    
    Args:
        bill_data: Dati della fattura
        output_file: Se specificato, salva l'anteprima in questo file
    """
    # Crea un'istanza fittizia dell'importatore fatture (non invierà nulla)
    importer = QuickBooksBillImporter(
        base_url="https://quickbooks.api.intuit.com",
        realm_id="dummy_realm",
        access_token="dummy_token"
    )
    
    # Costruisci il payload senza inviarlo
    bill_payload = importer._build_bill_payload(bill_data)
    
    # Visualizza il payload formattato
    formatted_payload = json.dumps(bill_payload, indent=2, ensure_ascii=False)
    print("\n===== ANTEPRIMA PAYLOAD FATTURA FORNITORE QUICKBOOKS =====")
    print(formatted_payload)
    print("==========================================================\n")
    
    # Salva su file se richiesto
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_payload)
            print(f"Anteprima payload salvata in: {output_file}")
        except Exception as e:
            print(f"Errore nel salvataggio dell'anteprima: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Genera anteprima payload fattura QuickBooks")
    parser.add_argument("-f", "--file", help="Percorso del file JSON con i dati della fattura")
    parser.add_argument("-o", "--output", help="Percorso del file di output per salvare l'anteprima")
    args = parser.parse_args()
    
    try:
        print("Avvio generazione anteprima payload...")
        
        if args.file:
            print(f"Caricamento dati da file: {args.file}")
            bill_data = load_bill_data_from_file(args.file)
        else:
            bill_data = create_sample_bill_data()
            print("Nessun file di input specificato, utilizzo dati di esempio.")
        
        print(f"Dati fattura: {json.dumps(bill_data, indent=2)[:200]}...")
        preview_bill_payload(bill_data, args.output)
        print("Anteprima completata con successo.")
    except Exception as e:
        print(f"ERRORE DURANTE L'ESECUZIONE: {str(e)}")
        import traceback
        print(traceback.format_exc())
