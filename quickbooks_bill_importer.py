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
            "Content-Type": "application/json"        }
    
    def create_bill(self, bill_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/v3/company/{self.realm_id}/bill"
        # Normalizza le date in formato YYYY-MM-DD
        from datetime import datetime
        def normalize_date(val):
            if not val:
                return None
            try:
                # Prova prima formato MM/DD/YYYY (formato americano - più comune per fatture)
                dt = datetime.strptime(val, "%m/%d/%Y")
                # logging.info(f"[normalize_date] Data convertita da formato americano {val} a {dt.strftime('%Y-%m-%d')}")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    # Se già in formato ISO corretto YYYY-MM-DD
                    dt = datetime.strptime(val, "%Y-%m-%d")
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        # Prova formato DD/MM/YYYY (formato italiano) come fallback
                        dt = datetime.strptime(val, "%d/%m/%Y")
                        # logging.info(f"[normalize_date] Data convertita da formato italiano {val} a {dt.strftime('%Y-%m-%d')}")
                        return dt.strftime("%Y-%m-%d")
                    except Exception:
                        # logging.warning(f"[normalize_date] Data non convertita: {val}")
                        return val  # Lascia invariato per debug
        if 'txn_date' in bill_data:
            bill_data['txn_date'] = normalize_date(bill_data['txn_date'])
        if 'due_date' in bill_data and bill_data['due_date']:
            bill_data['due_date'] = normalize_date(bill_data['due_date'])
        # Logga l'intero payload della fattura in modo leggibile
        import json
        # logging.info("[create_bill] PAYLOAD COMPLETO:\n" + json.dumps(bill_data, ensure_ascii=False, indent=2))
        if not self._validate_bill_data(bill_data):
            # print("[create_bill] Dati fattura non validi, abortisco.")
            return None
        # Log bill creation details
        #logging.info(f"[create_bill] Preparing to create bill: vendor_id={bill_data.get('vendor_id')} ref_number={bill_data.get('ref_number')} txn_date={bill_data.get('txn_date')} line_items={len(bill_data.get('line_items', []))}")
        payload = self._build_bill_payload(bill_data)        # Debug log full payload - ATTIVATO PER DEBUG VENDOR
        # logging.info(f"[create_bill] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        # NON stampare più il payload
        try:
            #logging.info(f"[create_bill] Invio richiesta a: {url}")
            # logging.debug(f"[create_bill] Payload: {json.dumps(payload, indent=2)}")  # RIMOSSO
            response = requests.post(url, headers=self.headers, json=payload)
            # print(f"[create_bill] Risposta ricevuta: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                # print(f"[create_bill] Risposta JSON completa: Bill creata con successo")
                bill_created = result.get("Bill")
                if not bill_created:
                    bill_created = result.get("QueryResponse", {}).get("Bill", [])
                if bill_created:
                    bill_id = bill_created[0].get("Id") if isinstance(bill_created, list) else bill_created.get("Id")
                    # print(f"[create_bill] Fattura creata con successo. ID: {bill_id}")
                    #logging.info(f"[create_bill] Fattura creata con successo. ID: {bill_id}")
                    #print(f"[create_bill] Fattura creata con successo. ID: {bill_id}")
                    return result
                else:
                    # print("[create_bill] Risposta senza dati della fattura")
                    logging.error("[create_bill] Risposta senza dati della fattura")
                    return result
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = response.text
                # print(f"[create_bill] Errore {response.status_code}")
                logging.error(f"[create_bill] Errore {response.status_code}")
                self._handle_error(response, "create_bill")
                return {"error": error_data, "status_code": response.status_code}
        except Exception as e:
            # print(f"[create_bill] Errore durante la creazione: {str(e)}")
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
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {
            'success_count': 0,
            'error_count': 0,
            'created_bills': [],
            'errors': []
        }
        max_workers = min(10, len(bills_list))  # Limita il numero di thread per non saturare l'API
        def process_one(bill_data):
            logging.info(f"[batch_import] Processando fattura ref_number={bill_data.get('ref_number')}")
            return self.create_bill(bill_data)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_bill = {executor.submit(process_one, bill): bill for bill in bills_list}
            for future in as_completed(future_to_bill):
                bill_data = future_to_bill[future]
                try:
                    result = future.result()
                    if result:
                        results['success_count'] += 1
                        results['created_bills'].append(result)
                    else:
                        results['error_count'] += 1
                        results['errors'].append(f"Errore fattura: {bill_data.get('ref_number', 'N/A')}")
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append(f"Errore fattura: {bill_data.get('ref_number', 'N/A')} - {str(e)}")
        logging.info(f"[batch_import] Completato. Successi: {results['success_count']}, Errori: {results['error_count']}")
        return results

    def _validate_bill_data(self, bill_data: Dict[str, Any]) -> bool:
        required_fields = ['vendor_id', 'line_items']
        for field in required_fields:
            if field not in bill_data or not bill_data[field]:
                # print(f"[validate_bill_data] Campo obbligatorio mancante: {field}")
                logging.error(f"[validate_bill_data] Campo obbligatorio mancante: {field}")
                return False
        if not isinstance(bill_data['line_items'], list) or len(bill_data['line_items']) == 0:
            # print("[validate_bill_data] line_items deve essere una lista non vuota")
            logging.error("[validate_bill_data] line_items deve essere una lista non vuota")
            return False
        return True

    def _build_bill_payload(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        # print(f"[_build_bill_payload] Costruzione payload per la bill...")
        bill_payload = {
            "VendorRef": {
                "value": str(bill_data['vendor_id'])
            },
            "Line": []        }        # Normalizza date in formato YYYY-MM-DD
        def normalize_date(val):
            if not val:
                return None
            try:
                # Prova prima formato MM/DD/YYYY (formato americano - più comune per fatture)
                dt = datetime.strptime(val, "%m/%d/%Y")
                # logging.info(f"[normalize_date] Data convertita da formato americano {val} a {dt.strftime('%Y-%m-%d')}")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    # Se già in formato ISO corretto YYYY-MM-DD
                    dt = datetime.strptime(val, "%Y-%m-%d")
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    try:
                        # Prova formato DD/MM/YYYY (formato italiano) come fallback
                        dt = datetime.strptime(val, "%d/%m/%Y")
                        # logging.info(f"[normalize_date] Data convertita da formato italiano {val} a {dt.strftime('%Y-%m-%d')}")
                        return dt.strftime("%Y-%m-%d")
                    except Exception:
                        # logging.warning(f"[normalize_date] Data non convertita: {val}")
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
                "TxnTaxCodeRef": {"value": str(bill_data['taxcode_id'])}
            }
        # ---
        for i, line_item in enumerate(bill_data['line_items']):
            line = self._build_line_item(line_item, i + 1)
            if line:
                bill_payload["Line"].append(line)
        # print(f"[_build_bill_payload] Payload pronto (sintetico)")
        return bill_payload

    def _build_line_item(self, line_item: Dict[str, Any], line_num: int) -> Optional[Dict[str, Any]]:
        if 'amount' not in line_item:
            # print(f"[build_line_item] Riga {line_num}: amount mancante")
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
                }
            }
            if line_item.get('quantity'):
                line["ItemBasedExpenseLineDetail"]["Qty"] = float(line_item['quantity'])
            if line_item.get('unit_price'):
                line["ItemBasedExpenseLineDetail"]["UnitPrice"] = float(line_item['unit_price'])
        else:
            line["AccountBasedExpenseLineDetail"] = {
                "AccountRef": {
                    "value": str(line_item.get('account_id', '1'))
                }
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
        # print(f"[build_line_item] Riga {line_num} costruita (sintetico)")
        return line

    def _handle_error(self, response: requests.Response, operation: str):
        try:
            error_data = response.json()
            fault = error_data.get("Fault", {})
            error_details = fault.get("Error", [{}])
            if error_details:
                error_msg = error_details[0].get("Detail", "Errore sconosciuto")
                error_code = error_details[0].get("code", "N/A")
                logging.error(f"[{operation}] Errore {response.status_code} - Codice: {error_code}, Dettaglio: {error_msg}")
            else:
                logging.error(f"[{operation}] Errore {response.status_code} - {response.text}")
        except:
            logging.error(f"[{operation}] Errore {response.status_code} - {response.text}")

    def find_or_create_vendor(self, vendor_name: str, vendor_data: Dict[str, Any] = None) -> Optional[str]:
        """
        Cerca un fornitore per nome (query mirata), se non esiste lo crea
        """
        vendors = self.get_vendors(name=vendor_name)
        if vendors:
            for vendor in vendors:
                if vendor.get('DisplayName', '').lower() == vendor_name.lower():
                    vendor_id = vendor.get('Id')
                    return vendor_id
        create_data = vendor_data or {}
        create_data['name'] = vendor_name
        result = self.create_vendor(create_data)
        if result:
            vendor_created = result.get("QueryResponse", {}).get("Vendor") or result.get("Vendor")
            if vendor_created:
                vendor_id = vendor_created[0].get("Id") if isinstance(vendor_created, list) else vendor_created.get("Id")
                return vendor_id
        return None

    def get_vendors(self, name: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Recupera la lista dei fornitori da QuickBooks. Se name è fornito, cerca solo quel fornitore (query mirata).
        """
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        if name:
            # QuickBooks Online richiede l'apostrofo escapato come \' nelle query
            safe_name = name.replace("'", "\\'")
            query = f"SELECT * FROM Vendor WHERE DisplayName = '{safe_name}'"
        else:
            query = "SELECT * FROM Vendor"
        params = {"query": query}
        # print(f"[get_vendors] Recupero lista fornitori... (query: {query})")
        try:
            response = requests.get(url, headers=self.headers, params=params)
            # print(f"[get_vendors] Risposta: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                # print(f"[get_vendors] Fornitori trovati: {len(data.get('QueryResponse', {}).get('Vendor', []))}")
                return data.get("QueryResponse", {}).get("Vendor", [])
            else:
                # print(f"[get_vendors] Errore {response.status_code}: {response.text}")
                logging.error(f"[get_vendors] Errore {response.status_code}: {response.text}")
                return None
        except Exception as e:
            # print(f"[get_vendors] Errore: {e}")
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
        for key in ["PrimaryEmailAddr", "PrimaryPhone", "CompanyName", "TaxIdentifier", "BillAddr"]:
            if key in vendor_data:
                payload[key] = vendor_data[key]
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code in (200, 201):
                return response.json()
            else:
                # logging.error(f"[create_vendor] Errore {response.status_code}: {response.text}")
                # Gestione errore 6240 (Duplicate Name Exists)
                try:
                    err_json = response.json()
                    errors = err_json.get("Fault", {}).get("Error", [])
                    for err in errors:
                        if err.get("code") == "6240" and ("Duplicate Name Exists" in err.get("Message", "") or "duplicato" in err.get("Message", "").lower()):
                            # print(f"[create_vendor] Errore 6240 - Vendor duplicato '{payload['DisplayName']}'. Provo solo con suffisso .2...")
                            # logging.warning(f"[create_vendor] Errore 6240 - Vendor duplicato '{payload['DisplayName']}'. Provo solo con suffisso .2...")
                            base_name = payload['DisplayName']
                            url_query = f"{self.base_url}/v3/company/{self.realm_id}/query"
                            new_name = f"{base_name}.2"
                            safe_new_name = new_name.replace("'", "''")
                            # 1. Controlla se esiste già come vendor
                            query_vendor = f"SELECT * FROM Vendor WHERE DisplayName = '{safe_new_name}'"
                            params_vendor = {"query": query_vendor}
                            resp_vendor = requests.get(url_query, headers=self.headers, params=params_vendor)
                            if resp_vendor.status_code == 200:
                                data_vendor = resp_vendor.json()
                                vendors = data_vendor.get('QueryResponse', {}).get('Vendor', [])
                                if vendors:
                                    # print(f"[create_vendor] Vendor già esistente con nome {new_name}: {vendors[0]}")
                                    # logging.info(f"[create_vendor] Vendor già esistente con nome {new_name}: {vendors[0]}")
                                    return {"Vendor": vendors[0]}
                            # 2. Controlla se esiste già come customer
                            query_customer = f"SELECT * FROM Customer WHERE DisplayName = '{safe_new_name}'"
                            params_customer = {"query": query_customer}
                            resp_customer = requests.get(url_query, headers=self.headers, params=params_customer)
                            if resp_customer.status_code == 200:
                                data_customer = resp_customer.json()
                                customers = data_customer.get('QueryResponse', {}).get('Customer', [])
                                if customers:
                                    # print(f"[create_vendor] Customer già esistente con nome {new_name}, impossibile creare vendor.")
                                    logging.error(f"[create_vendor] Customer già esistente con nome {new_name}, impossibile creare vendor.")
                                    return None
                            # 3. Se non esiste né come vendor né come customer, crea il vendor con il nuovo nome
                            payload['DisplayName'] = new_name
                            response2 = requests.post(url, headers=self.headers, json=payload)
                            # print(f"[create_vendor] Risposta tentativo .2: {response2.status_code}")
                            # logging.info(f"[create_vendor] Risposta tentativo .2: {response2.status_code}")
                            if response2.status_code in (200, 201):
                                # print(f"[create_vendor] Vendor creato con nome alternativo: {new_name}")
                                # logging.info(f"[create_vendor] Vendor creato con nome alternativo: {new_name}")
                                return response2.json()
                            # print(f"[create_vendor] Impossibile creare vendor con nome alternativo: {new_name}")
                            logging.error(f"[create_vendor] Impossibile creare vendor con nome alternativo: {new_name}")
                            return None
                except Exception as e2:
                    # print(f"[create_vendor] Errore parsing errore duplicato vendor: {e2}")
                    logging.error(f"[create_vendor] Errore parsing errore duplicato vendor: {e2}")
                return None
        except Exception as e:
            # print(f"[create_vendor] Errore: {e}")
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
                # print(f"[validate_bill_payload] Campo obbligatorio mancante: {field}")
                return False
        # VendorRef deve avere value
        if not isinstance(payload["VendorRef"], dict) or not payload["VendorRef"].get("value"):
            # print("[validate_bill_payload] VendorRef.value mancante")
            return False
        # Line deve essere lista non vuota
        if not isinstance(payload["Line"], list) or not payload["Line"]:
            # print("[validate_bill_payload] Line deve essere una lista non vuota")
            return False
        # TxnDate deve essere YYYY-MM-DD
        try:
            datetime.strptime(payload["TxnDate"], "%Y-%m-%d")
        except Exception:
            # print(f"[validate_bill_payload] TxnDate non valida: {payload['TxnDate']}")
            return False
        # Opzionale: DueDate se presente deve essere YYYY-MM-DD
        if payload.get("DueDate"):
            try:
                datetime.strptime(payload["DueDate"], "%Y-%m-%d")
            except Exception:
                # print(f"[validate_bill_payload] DueDate non valida: {payload['DueDate']}")
                return False        # Normalizza e valida TxnDate e DueDate (accetta anche formati DD/MM/YYYY e MM/DD/YYYY e li trasforma)
        for date_field in ["TxnDate", "DueDate"]:
            if payload.get(date_field):
                val = payload[date_field]
                # Se già in formato YYYY-MM-DD, ok
                try:
                    datetime.strptime(val, "%Y-%m-%d")
                except ValueError:
                    # Prova prima a convertire da MM/DD/YYYY (formato americano - più comune)
                    try:
                        dt = datetime.strptime(val, "%m/%d/%Y")
                        payload[date_field] = dt.strftime("%Y-%m-%d")
                        # print(f"[validate_bill_payload] {date_field} convertita da formato americano in formato valido: {payload[date_field]}")
                    except ValueError:
                        # Prova a convertire da DD/MM/YYYY (formato italiano) come fallback
                        try:
                            dt = datetime.strptime(val, "%d/%m/%Y")
                            payload[date_field] = dt.strftime("%Y-%m-%d")
                            # print(f"[validate_bill_payload] {date_field} convertita da formato italiano in formato valido: {payload[date_field]}")
                        except Exception:
                            # print(f"[validate_bill_payload] {date_field} non valida: {val}")
                            return False
        # print("[validate_bill_payload] Payload valido secondo la documentazione base.")
        return True
