#!/usr/bin/env python
# -*- coding: utf-8 -*-
# generate_bill_payload_preview.py - Genera un esempio di payload JSON per QuickBooks

import json
import os
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

def build_bill_payload(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Costruisce un payload di fattura compatibile con QuickBooks"""
    bill_payload = {
        "VendorRef": {
            "value": str(bill_data['vendor_id'])
        },
        "CurrencyRef": {
            "value": "EUR",
            "name": "Euro"
        },
        "APAccountRef": {
            "value": "37",  # Imposta un ID fisso per Accounts Payable
            "name": "Accounts Payable"
        },
        "ExchangeRate": 1.0,
        "GlobalTaxCalculation": "TaxExcluded",
        "Line": []
    }
    
    # Imposta date e altri campi
    bill_payload["TxnDate"] = bill_data.get('txn_date') or "2025-05-30"
    if bill_data.get('due_date'):
        bill_payload["DueDate"] = bill_data['due_date']
    if bill_data.get('ref_number'):
        bill_payload["DocNumber"] = bill_data['ref_number']
    if bill_data.get('memo'):
        bill_payload["PrivateNote"] = bill_data['memo']
        
    # Integrazione TaxCode
    bill_payload["TxnTaxDetail"] = {
        "TotalTax": 0.00
    }
    
    # Costruisci le righe della fattura
    for i, line_item in enumerate(bill_data['line_items']):
        line = build_line_item(line_item, i + 1)
        if line:
            bill_payload["Line"].append(line)
    
    # Calcola e imposta il totale
    total_amount = 0.0
    if bill_data.get('total_amount'):
        total_amount = float(bill_data['total_amount'])
    else:
        total_amount = sum(float(line.get('Amount', 0)) for line in bill_payload["Line"])
    
    # Imposta il totale e arrotonda a 2 decimali
    bill_payload["TotalAmt"] = round(total_amount, 2)
        
    return bill_payload

def build_line_item(line_item: Dict[str, Any], line_num: int) -> Dict[str, Any]:
    """Costruisce una riga di fattura compatibile con QuickBooks"""
    if 'amount' not in line_item:
        print(f"Riga {line_num}: amount mancante")
        return None
    
    # Formattazione base della riga
    line = {
        "Id": str(line_num),
        "LineNum": line_num,
        "Amount": round(float(line_item['amount']), 2),  # Arrotonda a 2 decimali
        "DetailType": "AccountBasedExpenseLineDetail"
    }
    
    # Gestione delle righe basate su articoli (item)
    if line_item.get('item_id'):
        line["DetailType"] = "ItemBasedExpenseLineDetail"
        line["ItemBasedExpenseLineDetail"] = {
            "ItemRef": {
                "value": str(line_item['item_id'])
            },
            "BillableStatus": "NotBillable",
            "TaxCodeRef": {"value": "NON"}  # Imposta valore predefinito
        }
        
        if line_item.get('quantity'):
            line["ItemBasedExpenseLineDetail"]["Qty"] = float(line_item['quantity'])
        if line_item.get('unit_price'):
            line["ItemBasedExpenseLineDetail"]["UnitPrice"] = round(float(line_item['unit_price']), 2)
            
        # Aggiunge TaxCodeRef se presente
        if line_item.get('taxcode_id'):
            line["ItemBasedExpenseLineDetail"]["TaxCodeRef"] = {"value": str(line_item['taxcode_id'])}
    else:        # Righe basate su conto (account)
        line["AccountBasedExpenseLineDetail"] = {
            "AccountRef": {
                "value": str(line_item.get('account_id', '1'))
            },
            "BillableStatus": "NotBillable",
            "TaxCodeRef": {"value": "NON"}  # Imposta valore predefinito
        }
        
        # Aggiunge TaxCodeRef se presente
        if line_item.get('taxcode_id'):
            line["AccountBasedExpenseLineDetail"]["TaxCodeRef"] = {"value": str(line_item['taxcode_id'])}
    
    # Aggiungi descrizione se presente
    if line_item.get('description'):
        line["Description"] = line_item['description']
    
    # Gestione del cliente se presente
    if line_item.get('customer_id'):
        if "ItemBasedExpenseLineDetail" in line:
            line["ItemBasedExpenseLineDetail"]["CustomerRef"] = {
                "value": str(line_item['customer_id'])
            }
        else:
            line["AccountBasedExpenseLineDetail"]["CustomerRef"] = {
                "value": str(line_item['customer_id'])
            }
            
    return line

def main():
    """Funzione principale"""
    bill_data = create_sample_bill_data()
    bill_payload = build_bill_payload(bill_data)
    
    # Salva il payload su file
    output_file = "test_bill_payload_updated.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(bill_payload, f, indent=2, ensure_ascii=False)
    
    print(f"Payload di esempio salvato in: {output_file}")
    print("Per una visualizzazione più dettagliata, aprire il file JSON generato.")
    
    # Stampa riepilogo
    print("\nRiepilogo Payload:")
    print(f"Fornitore ID: {bill_payload['VendorRef']['value']}")
    print(f"Data fattura: {bill_payload['TxnDate']}")
    print(f"Numero fattura: {bill_payload.get('DocNumber', 'N/A')}")
    print(f"Righe: {len(bill_payload['Line'])}")
    print(f"Totale: {bill_payload['TotalAmt']}")

if __name__ == "__main__":
    main()