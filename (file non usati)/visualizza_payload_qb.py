#!/usr/bin/env python
# -*- coding: utf-8 -*-
# visualizza_payload_qb.py - Visualizza il payload esatto inviato a QuickBooks

import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Importa le classi necessarie
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from quickbooks_bill_importer import QuickBooksBillImporter
from quickbooks_bill_importer_with_grouping import QuickBooksBillImporterWithGrouping
from bill_grouping_system import BillGroupingSystem

def create_sample_bill() -> Dict[str, Any]:
    """Crea una fattura di esempio"""
    return {
        'vendor_id': '56',  # Cambia con un ID valido dal tuo QuickBooks
        'vendor_name': 'Fornitore Test',
        'ref_number': 'TEST-001',
        'txn_date': '2025-05-31',
        'due_date': '2025-06-30',
        'memo': 'Fattura di test per visualizzazione payload',
        'line_items': [
            {
                'amount': 100.00,
                'description': 'Servizio Test 1',
                'account_id': '54',  # Cambia con un ID valido dal tuo QuickBooks
                'taxcode_id': '2'  # Cambia con un ID valido dal tuo QuickBooks
            },
            {
                'amount': 200.00,
                'description': 'Servizio Test 2',
                'account_id': '55',  # Cambia con un ID valido dal tuo QuickBooks
                'taxcode_id': '2'  # Cambia con un ID valido dal tuo QuickBooks
            }
        ],
        'total_amount': 300.00
    }

def visualizza_payload_normale():
    """Visualizza il payload di una fattura normale"""
    print("\n=== PAYLOAD FATTURA NORMALE ===")
    
    # Crea una fattura di esempio
    bill_data = create_sample_bill()
    
    # Crea l'importatore
    importer = QuickBooksBillImporter(
        base_url="https://sandbox-quickbooks.api.intuit.com",
        realm_id="test_realm",
        access_token="test_token"
    )
    
    # Genera il payload
    payload = importer._build_bill_payload(bill_data)
    
    # Visualizza il payload
    print("\nJSON Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # Salva il payload
    with open("payload_normale.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    print(f"\nPayload salvato in: payload_normale.json")
    return payload

def visualizza_payload_raggruppato():
    """Visualizza il payload di una fattura raggruppata"""
    print("\n=== PAYLOAD FATTURA RAGGRUPPATA ===")
    
    # Crea fatture di esempio
    bill1 = create_sample_bill()
    bill2 = create_sample_bill()
    bill2['ref_number'] = 'TEST-002'
    bill2['line_items'][0]['description'] = 'Servizio Test 3'
    bill2['line_items'][1]['description'] = 'Servizio Test 4'
    
    # Crea il sistema di raggruppamento
    grouping_system = BillGroupingSystem()
    
    # Configura regole di raggruppamento
    grouping_system.set_grouping_rules({
        'by_vendor': True,
        'merge_same_account': True
    })
    
    # Aggiungi le fatture
    grouping_system.add_bill_for_grouping(bill1)
    grouping_system.add_bill_for_grouping(bill2)
    
    # Ottieni le fatture raggruppate
    grouped_bills = grouping_system.get_grouped_bills()
    
    if not grouped_bills:
        print("Nessuna fattura raggruppata generata!")
        return None
    
    # Ottieni i dati della fattura raggruppata
    grouped_bill_data = grouping_system.get_grouped_bill_data_for_qb(grouped_bills[0])
    
    # Visualizza i dati prima della conversione
    print("\nDati fattura raggruppata prima della conversione:")
    print(json.dumps(grouped_bill_data, indent=2, default=str, ensure_ascii=False))
    
    # Crea l'importatore
    importer = QuickBooksBillImporter(
        base_url="https://sandbox-quickbooks.api.intuit.com",
        realm_id="test_realm",
        access_token="test_token"
    )
    
    # Genera il payload
    payload = importer._build_bill_payload(grouped_bill_data)
    
    # Visualizza il payload
    print("\nJSON Payload dopo la conversione:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    # Salva il payload
    with open("payload_raggruppato.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    
    # Salva anche i dati intermedi
    with open("dati_fattura_raggruppata.json", "w", encoding="utf-8") as f:
        json.dump(grouped_bill_data, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\nPayload salvato in: payload_raggruppato.json")
    print(f"Dati intermedi salvati in: dati_fattura_raggruppata.json")
    return payload

def confronta_payloads(normal_payload: Dict[str, Any], grouped_payload: Dict[str, Any]):
    """Confronta i payload normale e raggruppato per verificare le differenze"""
    print("\n=== CONFRONTO PAYLOADS ===")
    
    # Estrai le chiavi
    normal_keys = set(normal_payload.keys())
    grouped_keys = set(grouped_payload.keys())
    
    # Chiavi comuni
    common_keys = normal_keys.intersection(grouped_keys)
    
    # Chiavi diverse
    only_in_normal = normal_keys - grouped_keys
    only_in_grouped = grouped_keys - normal_keys
    
    print(f"Chiavi comuni: {len(common_keys)}")
    print(f"Solo nel payload normale: {len(only_in_normal)}")
    if only_in_normal:
        print(f"  {', '.join(only_in_normal)}")
    
    print(f"Solo nel payload raggruppato: {len(only_in_grouped)}")
    if only_in_grouped:
        print(f"  {', '.join(only_in_grouped)}")
    
    # Controlla valori diversi nelle chiavi comuni
    different_values = {}
    for key in common_keys:
        if normal_payload[key] != grouped_payload[key]:
            different_values[key] = {
                "normale": normal_payload[key],
                "raggruppato": grouped_payload[key]
            }
    
    if different_values:
        print("\nValori diversi nelle chiavi comuni:")
        for key, values in different_values.items():
            print(f"- {key}:")
            print(f"  Normale: {values['normale']}")
            print(f"  Raggruppato: {values['raggruppato']}")
    else:
        print("\n✅ Tutti i valori nelle chiavi comuni sono identici!")
    
    # Confronta struttura delle linee
    if "Line" in normal_payload and "Line" in grouped_payload:
        normal_line = normal_payload["Line"][0] if normal_payload["Line"] else {}
        grouped_line = grouped_payload["Line"][0] if grouped_payload["Line"] else {}
        
        normal_line_keys = set(normal_line.keys())
        grouped_line_keys = set(grouped_line.keys())
        
        only_in_normal_line = normal_line_keys - grouped_line_keys
        only_in_grouped_line = grouped_line_keys - normal_line_keys
        
        print("\nConfrontando la struttura delle linee:")
        print(f"Solo nella linea normale: {', '.join(only_in_normal_line) if only_in_normal_line else 'nessuna'}")
        print(f"Solo nella linea raggruppata: {', '.join(only_in_grouped_line) if only_in_grouped_line else 'nessuna'}")
        
        # Confronta chiavi in DetailType
        normal_detail_type = normal_line.get("DetailType", "")
        grouped_detail_type = grouped_line.get("DetailType", "")
        
        if normal_detail_type != grouped_detail_type:
            print(f"\nDetailType diverso:")
            print(f"  Normale: {normal_detail_type}")
            print(f"  Raggruppato: {grouped_detail_type}")
        
        # Confronta il dettaglio specifico
        if normal_detail_type == "AccountBasedExpenseLineDetail" and grouped_detail_type == "AccountBasedExpenseLineDetail":
            normal_detail = normal_line.get("AccountBasedExpenseLineDetail", {})
            grouped_detail = grouped_line.get("AccountBasedExpenseLineDetail", {})
            
            normal_detail_keys = set(normal_detail.keys())
            grouped_detail_keys = set(grouped_detail.keys())
            
            only_in_normal_detail = normal_detail_keys - grouped_detail_keys
            only_in_grouped_detail = grouped_detail_keys - normal_detail_keys
            
            print("\nConfrontando il dettaglio della linea:")
            print(f"Solo nel dettaglio normale: {', '.join(only_in_normal_detail) if only_in_normal_detail else 'nessuna'}")
            print(f"Solo nel dettaglio raggruppato: {', '.join(only_in_grouped_detail) if only_in_grouped_detail else 'nessuna'}")

def main():
    """Funzione principale"""
    print("=== VISUALIZZAZIONE PAYLOAD QUICKBOOKS ===")
    print("Questo script genera e confronta i payload JSON inviati a QuickBooks")
    print("per fatture normali e raggruppate, per verificare che siano identici.")
    
    # Genera i payload
    normal_payload = visualizza_payload_normale()
    grouped_payload = visualizza_payload_raggruppato()
    
    # Confronta i payload
    if normal_payload and grouped_payload:
        confronta_payloads(normal_payload, grouped_payload)
    
    print("\nOperazione completata. Controlla i file JSON generati per maggiori dettagli.")

if __name__ == "__main__":
    main()
