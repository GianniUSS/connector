import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

class QuickBooksBillImporter:
    """
    Classe per importare fatture di acquisto (Bills) su QuickBooks Online
    """
    def __init__(self, base_url: str, realm_id: str, access_token: str):
        self.base_url = base_url.rstrip('/')
        self.realm_id = realm_id
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def create_bill(self, bill_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        print(f"[create_bill] Inizio creazione fattura")
        if not self._validate_bill_data(bill_data):
            print("[create_bill] Dati fattura non validi, abortisco.")
            return None
        
        # Controllo se la fattura esiste già
        vendor_id = bill_data.get('vendor_id')
        doc_number = bill_data.get('ref_number')
        
        if vendor_id and doc_number:
            existing_bill = self.check_existing_bill(vendor_id, doc_number)
            if existing_bill:
                print(f"[create_bill] 🔄 Fattura già presente in QuickBooks: DocNumber={doc_number}, VendorRef={vendor_id}")
                logging.info(f"[create_bill] Fattura già esistente saltata: DocNumber={doc_number}")
                return {
                    "Bill": existing_bill,
                    "skipped": True,
                    "message": f"Fattura già esistente: DocNumber={doc_number}"
                }
        
        url = f"{self.base_url}/v3/company/{self.realm_id}/bill"
        print(f"[create_bill] Invio richiesta creazione a: {url}")
        payload = self._build_bill_payload(bill_data)
        # NON stampare più il payload
        try:
            logging.info(f"[create_bill] > : {url}")
            # logging.debug(f"[create_bill] Payload: {json.dumps(payload, indent=2)}")  # RIMOSSO
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"[create_bill] Risposta ricevuta: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"[create_bill] Risposta JSON completa: Bill creata con successo")
                bill_created = result.get("Bill")
                if not bill_created:
                    bill_created = result.get("QueryResponse", {}).get("Bill", [])
                if bill_created:
                    bill_id = bill_created[0].get("Id") if isinstance(bill_created, list) else bill_created.get("Id")
                    print(f"[create_bill] Fattura creata con successo. ID: {bill_id}")
                    logging.info(f"[create_bill] Fattura creata con successo. ID: {bill_id}")
                    return result
                else:
                    print("[create_bill] Risposta senza dati della fattura")
                    logging.error("[create_bill] Risposta senza dati della fattura")
                    return result
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = response.text
                print(f"[create_bill] Errore {response.status_code}")
                logging.error(f"[create_bill] Errore {response.status_code}")
                self._handle_error(response, "create_bill")
                return {"error": error_data, "status_code": response.status_code}
        except Exception as e:
            print(f"[create_bill] Errore durante la creazione: {str(e)}")
            logging.error(f"[create_bill] Errore durante la creazione: {str(e)}")
            return {"error": str(e)}

    def create_bill_simple(self, vendor_id: str, txn_date: str, total_amount: float, line_items: List[Dict[str, Any]], due_date: Optional[str] = None, ref_number: Optional[str] = None, memo: Optional[str] = None) -> Optional[Dict[str, Any]]:
        bill_data = {
            'vendor_id': vendor_id,
            'txn_date': txn_date,
            'total_amount': total_amount,
            'line_items': line_items,
            'due_date': due_date,
            'ref_number': ref_number,
            'memo': memo
        }
        return self.create_bill(bill_data)

    def batch_import_bills(self, bills_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = {
            'success_count': 0,
            'error_count': 0,
            'skipped_count': 0,
            'created_bills': [],
            'skipped_bills': [],
            'errors': []
        }
        print(f"[batch_import] Inizio importazione di {len(bills_list)} fatture...")
        for i, bill_data in enumerate(bills_list):
            print(f"[batch_import] Processando fattura {i+1}/{len(bills_list)}")
            logging.info(f"[batch_import] Processando fattura {i+1}/{len(bills_list)}")
            result = self.create_bill(bill_data)
            if result:
                if result.get('skipped', False):
                    # Fattura saltata perché duplicata
                    results['skipped_count'] += 1
                    results['skipped_bills'].append(result)
                    print(f"[batch_import] Fattura {i+1} saltata: {bill_data.get('ref_number', 'N/A')}")
                    logging.info(f"[batch_import] Fattura saltata: {bill_data.get('ref_number', 'N/A')}")
                elif result.get('error'):
                    # Errore durante la creazione
                    results['error_count'] += 1
                    results['errors'].append(f"Errore fattura {i+1}: {bill_data.get('ref_number', 'N/A')} - {result.get('error', 'Errore sconosciuto')}")
                else:
                    # Fattura creata con successo
                    results['success_count'] += 1
                    results['created_bills'].append(result)
            else:
                results['error_count'] += 1
                results['errors'].append(f"Errore fattura {i+1}: {bill_data.get('ref_number', 'N/A')}")
        print(f"[batch_import] Completato. Successi: {results['success_count']}, Saltate: {results['skipped_count']}, Errori: {results['error_count']}")
        logging.info(f"[batch_import] Completato. Successi: {results['success_count']}, Saltate: {results['skipped_count']}, Errori: {results['error_count']}")
        return results

    def _validate_bill_data(self, bill_data: Dict[str, Any]) -> bool:
        required_fields = ['vendor_id', 'line_items']
        for field in required_fields:
            if field not in bill_data or not bill_data[field]:
                print(f"[validate_bill_data] Campo obbligatorio mancante: {field}")
                logging.error(f"[validate_bill_data] Campo obbligatorio mancante: {field}")
                return False
        if not isinstance(bill_data['line_items'], list) or len(bill_data['line_items']) == 0:
            print("[validate_bill_data] line_items deve essere una lista non vuota")
            logging.error("[validate_bill_data] line_items deve essere una lista non vuota")
            return False
        return True

    def _build_bill_payload(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[_build_bill_payload] Costruzione payload per la bill...")
        bill_payload = {
            "VendorRef": {
                "value": str(bill_data['vendor_id'])
            },
            "CurrencyRef": {
                "value": "EUR",
                "name": "Euro"
            },
            "APAccountRef": {
                "value": "ACCOUNTS_PAYABLE_ID",
                "name": "Accounts Payable"
            },
            "ExchangeRate": 1.0,
            "GlobalTaxCalculation": "TaxExcluded",
            "Line": []
        }
        # Normalizza date in formato YYYY-MM-DD
        def normalize_date(val):
            if not val:
                return None
            try:
                # Se già in formato corretto
                return datetime.strptime(val, "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                try:
                    # Prova DD/MM/YYYY
                    return datetime.strptime(val, "%d/%m/%Y").strftime("%Y-%m-%d")
                except Exception:
                    print(f"[_build_bill_payload] Data non valida: {val}")
                    return val  # Lascia invariato per debug
                    
        bill_payload["TxnDate"] = normalize_date(bill_data.get('txn_date')) or datetime.now().strftime('%Y-%m-%d')
        if bill_data.get('due_date'):
            bill_payload["DueDate"] = normalize_date(bill_data['due_date'])
        if bill_data.get('ref_number'):
            bill_payload["DocNumber"] = bill_data['ref_number']
        if bill_data.get('memo'):
            bill_payload["PrivateNote"] = bill_data['memo']
            
        # --- INTEGRAZIONE TAXCODE ---
        if bill_data.get('taxcode_id'):
            bill_payload["TxnTaxDetail"] = {
                "TxnTaxCodeRef": {"value": str(bill_data['taxcode_id'])},
                "TotalTax": 0.00
            }
        else:
            bill_payload["TxnTaxDetail"] = {
                "TotalTax": 0.00
            }
        # ---
        
        for i, line_item in enumerate(bill_data['line_items']):
            line = self._build_line_item(line_item, i + 1)
            if line:
                bill_payload["Line"].append(line)
        
        # Calcola il totale della fattura come somma delle righe o usa il valore fornito
        if bill_data.get('total_amount'):
            bill_payload["TotalAmt"] = float(bill_data['total_amount'])
        else:
            total_amount = sum(float(line.get('Amount', 0)) for line in bill_payload["Line"])
            bill_payload["TotalAmt"] = total_amount
            
        print(f"[_build_bill_payload] Payload pronto (sintetico)")
        return bill_payload

    def _build_line_item(self, line_item: Dict[str, Any], line_num: int) -> Optional[Dict[str, Any]]:
        if 'amount' not in line_item:
            print(f"[build_line_item] Riga {line_num}: amount mancante")
            logging.error(f"[build_line_item] Riga {line_num}: amount mancante")
            return None
        
        line = {
            "Id": str(line_num),
            "LineNum": line_num,
            "Amount": float(line_item['amount']),
            "DetailType": "AccountBasedExpenseLineDetail"
        }
        
        if line_item.get('item_id'):
            line["DetailType"] = "ItemBasedExpenseLineDetail"
            line["ItemBasedExpenseLineDetail"] = {
                "ItemRef": {
                    "value": str(line_item['item_id'])
                },
                "BillableStatus": "NotBillable"
            }
            
            if line_item.get('quantity'):
                line["ItemBasedExpenseLineDetail"]["Qty"] = float(line_item['quantity'])
            if line_item.get('unit_price'):
                line["ItemBasedExpenseLineDetail"]["UnitPrice"] = float(line_item['unit_price'])
        else:
            line["AccountBasedExpenseLineDetail"] = {
                "AccountRef": {
                    "value": str(line_item.get('account_id', '1')),
                    "name": "Spese Generali"
                },
                "BillableStatus": "NotBillable"
            }
            # --- INTEGRAZIONE TaxCodeRef a livello di riga ---
            # Se il bill_data contiene taxcode_id, aggiungilo anche qui
            # (passa taxcode_id come chiave su ogni line_item se serve)
            if line_item.get('taxcode_id'):
                line["AccountBasedExpenseLineDetail"]["TaxCodeRef"] = {"value": str(line_item['taxcode_id'])}
                
        if line_item.get('description'):
            line["Description"] = line_item['description']
            
        if line_item.get('customer_id'):
            if "ItemBasedExpenseLineDetail" in line:
                line["ItemBasedExpenseLineDetail"]["CustomerRef"] = {
                    "value": str(line_item['customer_id'])
                }
            else:
                line["AccountBasedExpenseLineDetail"]["CustomerRef"] = {
                    "value": str(line_item['customer_id'])
                }
                
        print(f"[build_line_item] Riga {line_num} costruita (sintetico)")
        return line

    def _handle_error(self, response: requests.Response, operation: str):
        try:
            error_data = response.json()
            fault = error_data.get("Fault", {})
            error_details = fault.get("Error", [{}])
            if error_details:
                error_msg = error_details[0].get("Detail", "Errore sconosciuto")
                error_code = error_details[0].get("code", "N/A")
                print(f"[{operation}] Errore {response.status_code} - Codice: {error_code}, Dettaglio: {error_msg}")
                logging.error(f"[{operation}] Errore {response.status_code} - Codice: {error_code}, Dettaglio: {error_msg}")
            else:
                print(f"[{operation}] Errore {response.status_code} - {response.text}")
                logging.error(f"[{operation}] Errore {response.status_code} - {response.text}")
        except:
            print(f"[{operation}] Errore {response.status_code} - {response.text}")
            logging.error(f"[{operation}] Errore {response.status_code} - {response.text}")

    def find_or_create_vendor(self, vendor_name: str, vendor_data: Dict[str, Any] = None) -> Optional[str]:
        """
        Cerca un fornitore per nome (query mirata), se non esiste lo crea
        """
        print(f"[find_or_create_vendor] Avvio ricerca/creazione vendor: {vendor_name}")
        # Ricerca mirata per nome
        vendors = self.get_vendors(name=vendor_name)
        print(f"[find_or_create_vendor] Fornitori trovati con nome '{vendor_name}': {len(vendors) if vendors else 0}")
        if vendors:
            for vendor in vendors:
                if vendor.get('DisplayName', '').lower() == vendor_name.lower():
                    vendor_id = vendor.get('Id')
                    print(f"[find_or_create_vendor] Fornitore trovato: {vendor_name} (ID: {vendor_id})")
                    logging.info(f"[find_or_create_vendor] Fornitore trovato: {vendor_name} (ID: {vendor_id})")
                    return vendor_id
        # Se non esiste, crealo
        print(f"[find_or_create_vendor] Fornitore {vendor_name} non trovato, creazione in corso...")
        logging.info(f"[find_or_create_vendor] Fornitore {vendor_name} non trovato, creazione in corso...")
        create_data = vendor_data or {}
        create_data['name'] = vendor_name
        result = self.create_vendor(create_data)
        print(f"[find_or_create_vendor] Risultato creazione vendor: {result}")
        if result:
            vendor_created = result.get("QueryResponse", {}).get("Vendor") or result.get("Vendor")
            print(f"[find_or_create_vendor] Oggetto vendor creato: {vendor_created}")
            if vendor_created:
                vendor_id = vendor_created[0].get("Id") if isinstance(vendor_created, list) else vendor_created.get("Id")
                print(f"[find_or_create_vendor] Fornitore creato: {vendor_name} (ID: {vendor_id})")
                logging.info(f"[find_or_create_vendor] Fornitore creato: {vendor_name} (ID: {vendor_id})")
                return vendor_id
        print(f"[find_or_create_vendor] Errore nella creazione o ricerca vendor: {vendor_name}")
        return None

    def get_vendors(self, name: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Recupera la lista dei fornitori da QuickBooks. Se name è fornito, cerca solo quel fornitore (query mirata).
        """
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        if name:
            # Escape singoli apici per la query QuickBooks
            safe_name = name.replace("'", "''")
            query = f"SELECT * FROM Vendor WHERE DisplayName = '{safe_name}'"
        else:
            query = "SELECT * FROM Vendor"
        params = {"query": query}
        print(f"[get_vendors] Recupero lista fornitori... (query: {query})")
        try:
            response = requests.get(url, headers=self.headers, params=params)
            print(f"[get_vendors] Risposta: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"[get_vendors] Fornitori trovati: {len(data.get('QueryResponse', {}).get('Vendor', []))}")
                return data.get("QueryResponse", {}).get("Vendor", [])
            else:
                print(f"[get_vendors] Errore {response.status_code}: {response.text}")
                logging.error(f"[get_vendors] Errore {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[get_vendors] Errore: {e}")
            logging.error(f"[get_vendors] Errore: {e}")
            return None

    def create_vendor(self, vendor_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Crea un nuovo fornitore in QuickBooks
        """
        url = f"{self.base_url}/v3/company/{self.realm_id}/vendor"
        payload = {
            "DisplayName": vendor_data.get("name") or vendor_data.get("DisplayName")
        }
        # Puoi aggiungere altri campi opzionali se presenti in vendor_data
        for key in ["PrimaryEmailAddr", "PrimaryPhone", "CompanyName", "TaxIdentifier", "BillAddr"]:
            if key in vendor_data:
                payload[key] = vendor_data[key]
        print(f"[create_vendor] Invio richiesta creazione fornitore: {payload}")
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            print(f"[create_vendor] Risposta: {response.status_code}")
            if response.status_code in (200, 201):
                print(f"[create_vendor] Fornitore creato con successo.")
                return response.json()
            else:
                print(f"[create_vendor] Errore {response.status_code}: {response.text}")
                logging.error(f"[create_vendor] Errore {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[create_vendor] Errore: {e}")
            logging.error(f"[create_vendor] Errore: {e}")
            return None

    def _validate_bill_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Valida la struttura del payload Bill secondo la documentazione QuickBooks.
        Controlla campi obbligatori e formato date.
        """
        required_fields = ["VendorRef", "Line", "TxnDate"]
        for field in required_fields:
            if field not in payload:
                print(f"[validate_bill_payload] Campo obbligatorio mancante: {field}")
                return False
        # VendorRef deve avere value
        if not isinstance(payload["VendorRef"], dict) or not payload["VendorRef"].get("value"):
            print("[validate_bill_payload] VendorRef.value mancante")
            return False
        # Line deve essere lista non vuota
        if not isinstance(payload["Line"], list) or not payload["Line"]:
            print("[validate_bill_payload] Line deve essere una lista non vuota")
            return False
        # TxnDate deve essere YYYY-MM-DD
        try:
            datetime.strptime(payload["TxnDate"], "%Y-%m-%d")
        except Exception:
            print(f"[validate_bill_payload] TxnDate non valida: {payload['TxnDate']}")
            return False
        # Opzionale: DueDate se presente deve essere YYYY-MM-DD
        if payload.get("DueDate"):
            try:
                datetime.strptime(payload["DueDate"], "%Y-%m-%d")
            except Exception:
                print(f"[validate_bill_payload] DueDate non valida: {payload['DueDate']}")
                return False
        # Normalizza e valida TxnDate e DueDate (accetta anche formati DD/MM/YYYY e li trasforma)
        for date_field in ["TxnDate", "DueDate"]:
            if payload.get(date_field):
                val = payload[date_field]
                # Se già in formato YYYY-MM-DD, ok
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    # Prova a convertire da DD/MM/YYYY
                    try:
                        dt = datetime.strptime(val, "%d/%m/%Y")
                        payload[date_field] = dt.strftime("%Y-%m-%d")
                        print(f"[validate_bill_payload] {date_field} convertita in formato valido: {payload[date_field]}")
                    except Exception:
                        print(f"[validate_bill_payload] {date_field} non valida: {val}")
                        return False
        print("[validate_bill_payload] Payload valido secondo la documentazione base.")
        return True

    def check_existing_bill(self, vendor_id: str, doc_number: str) -> Optional[Dict[str, Any]]:
        """
        Controlla se esiste già una fattura (Bill) con lo stesso fornitore e numero documento
        
        Args:
            vendor_id (str): ID del fornitore in QuickBooks
            doc_number (str): Numero del documento della fattura
            
        Returns:
            Optional[Dict[str, Any]]: Dati della fattura se esiste, None altrimenti
        """
        if not vendor_id or not doc_number:
            print("[check_existing_bill] vendor_id o doc_number mancanti")
            return None
        
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        query = f"SELECT * FROM Bill WHERE VendorRef = '{vendor_id}' AND DocNumber = '{doc_number}'"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        params = {"query": query}
        
        print(f"[check_existing_bill] Controllo fattura esistente: VendorRef={vendor_id}, DocNumber={doc_number}")
        logging.info(f"[check_existing_bill] Query: {query}")
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                bills = data.get("QueryResponse", {}).get("Bill", [])
                
                if bills:
                    # Fattura trovata
                    bill = bills[0] if isinstance(bills, list) else bills
                    bill_id = bill.get("Id")
                    print(f"[check_existing_bill] ✅ Fattura già esistente trovata: ID={bill_id}, DocNumber={doc_number}")
                    logging.info(f"[check_existing_bill] Fattura già esistente: ID={bill_id}, DocNumber={doc_number}")
                    return bill
                else:
                    # Fattura non trovata
                    print(f"[check_existing_bill] ❌ Nessuna fattura esistente trovata per DocNumber={doc_number}")
                    logging.info(f"[check_existing_bill] Nessuna fattura esistente per DocNumber={doc_number}")
                    return None
            else:
                print(f"[check_existing_bill] Errore nella query: {response.status_code} - {response.text}")
                logging.error(f"[check_existing_bill] Errore {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"[check_existing_bill] Errore durante il controllo: {str(e)}")
            logging.error(f"[check_existing_bill] Errore: {str(e)}")
            return None
