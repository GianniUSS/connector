import requests
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
import config

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
        self.item_cache: Dict[str, Optional[str]] = {}
        self.account_cache: Dict[str, Optional[str]] = {}
        self.default_item_id = getattr(config, 'DEFAULT_QB_ITEM_ID', None)
        if isinstance(self.default_item_id, str):
            self.default_item_id = self.default_item_id.strip() or None
        self.default_item_name = getattr(config, 'DEFAULT_QB_ITEM_NAME', None)
        if self.default_item_name:
            self.default_item_name = self.default_item_name.strip() or None
        self.default_item_type = getattr(config, 'DEFAULT_QB_ITEM_TYPE', 'Service') or 'Service'
        self.default_item_expense_account_id = getattr(config, 'DEFAULT_QB_ITEM_EXPENSE_ACCOUNT_ID', None)
        if isinstance(self.default_item_expense_account_id, str):
            self.default_item_expense_account_id = self.default_item_expense_account_id.strip() or None
        self.default_item_expense_account_name = getattr(config, 'DEFAULT_QB_ITEM_EXPENSE_ACCOUNT_NAME', None)
        if self.default_item_expense_account_name:
            self.default_item_expense_account_name = self.default_item_expense_account_name.strip() or None
        self.default_item_income_account_id = getattr(config, 'DEFAULT_QB_ITEM_INCOME_ACCOUNT_ID', None)
        if isinstance(self.default_item_income_account_id, str):
            self.default_item_income_account_id = self.default_item_income_account_id.strip() or None
        self.default_item_income_account_name = getattr(config, 'DEFAULT_QB_ITEM_INCOME_ACCOUNT_NAME', None)
        if self.default_item_income_account_name:
            self.default_item_income_account_name = self.default_item_income_account_name.strip() or None
        self.default_item_purchase_tax_code_id = getattr(config, 'DEFAULT_QB_ITEM_PURCHASE_TAX_CODE_ID', None)
        if isinstance(self.default_item_purchase_tax_code_id, str):
            self.default_item_purchase_tax_code_id = self.default_item_purchase_tax_code_id.strip() or None
        self.default_item_sales_tax_code_id = getattr(config, 'DEFAULT_QB_ITEM_SALES_TAX_CODE_ID', None)
        if isinstance(self.default_item_sales_tax_code_id, str):
            self.default_item_sales_tax_code_id = self.default_item_sales_tax_code_id.strip() or None
        self._tax_code_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._tax_code_cache_loaded = False
        self._default_item_checked = False
    
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
        payload = self._build_bill_payload(bill_data)
        # 🔍 LOG PAYLOAD COMPLETO PER DEBUG
        logging.info(f"[create_bill] PAYLOAD QuickBooks:\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
        try:
            logging.info(f"[create_bill] Invio richiesta a: {url}")
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
        # NON aggiungere TxnTaxDetail se le righe usano ItemBasedExpenseLineDetail
        # Il TaxCode deve essere solo sulle righe, altrimenti QuickBooks va in errore 6000
        has_item_based_lines = any(
            (item.get('item_id') or item.get('item_name') or item.get('quantity') is not None)
            for item in bill_data.get('line_items', [])
        )
        if bill_data.get('taxcode_id') and not has_item_based_lines:
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
        item_id = line_item.get('item_id') or self._resolve_line_item_item_id(line_item)
        if item_id:
            line_item['item_id'] = item_id
            line["DetailType"] = "ItemBasedExpenseLineDetail"
            item_detail: Dict[str, Any] = {
                "ItemRef": {
                    "value": str(item_id)
                }
            }
            if line_item.get('quantity') is not None:
                item_detail["Qty"] = float(line_item['quantity'])
            if line_item.get('unit_price') is not None:
                item_detail["UnitPrice"] = float(line_item['unit_price'])
            if line_item.get('taxcode_id'):
                item_detail["TaxCodeRef"] = {"value": str(line_item['taxcode_id'])}
            line["ItemBasedExpenseLineDetail"] = item_detail
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
                item_detail = line.get("ItemBasedExpenseLineDetail") or {}
                item_detail["CustomerRef"] = {
                    "value": str(line_item['customer_id'])
                }
                line["ItemBasedExpenseLineDetail"] = item_detail
            else:
                line["AccountBasedExpenseLineDetail"]["CustomerRef"] = {
                    "value": str(line_item['customer_id'])
                }
        # print(f"[build_line_item] Riga {line_num} costruita (sintetico)")
        return line

    def _resolve_line_item_item_id(self, line_item: Dict[str, Any]) -> Optional[str]:
        """Restituisce l'item_id da usare per una linea, sfruttando cache e configurazione."""
        item_id = line_item.get('item_id')
        if item_id:
            return str(item_id)
        item_name = line_item.get('item_name')
        resolved_id = None
        if item_name:
            resolved_id = self._get_item_id_by_name(item_name)
        if resolved_id:
            return resolved_id
        if self.default_item_id:
            return str(self.default_item_id)
        if self.default_item_name:
            resolved_id = self._ensure_default_item_exists(
                unit_price=line_item.get('unit_price'),
                taxcode_id=line_item.get('taxcode_id'),
                tax_percent=line_item.get('tax_percent')
            )
            if resolved_id:
                return resolved_id
        return None

    def _get_item_id_by_name(self, name: str) -> Optional[str]:
        if not name:
            return None
        key = name.strip().lower()
        if not key:
            return None
        if key in self.item_cache:
            cached = self.item_cache[key]
            return str(cached) if cached else None
        item = self.get_item_by_name(name)
        if item:
            item_id = item.get('Id')
            self.item_cache[key] = item_id
            return str(item_id)
        self.item_cache[key] = None
        return None

    def _ensure_default_item_exists(
        self,
        unit_price: Optional[Any] = None,
        taxcode_id: Optional[Any] = None,
        tax_percent: Optional[Any] = None
    ) -> Optional[str]:
        if not self.default_item_name:
            return None
        if self.default_item_id:
            return str(self.default_item_id)
        if not self._default_item_checked:
            self._default_item_checked = True
            item = self.get_item_by_name(self.default_item_name)
            if item:
                item_id = item.get('Id')
                self.default_item_id = item_id
                key = self.default_item_name.strip().lower()
                self.item_cache[key] = item_id
                return str(item_id)
            expense_account_id = self._resolve_account_id('expense')
            income_account_id = self._resolve_account_id('income')
            if not income_account_id:
                logging.warning("DEFAULT_QB_ITEM_NAME configurato ma nessun conto entrate disponibile: impossibile creare automaticamente l'articolo.")
                return None
            if not expense_account_id:
                logging.warning("DEFAULT_QB_ITEM_NAME configurato ma nessun conto spese disponibile: impossibile creare automaticamente l'articolo.")
                return None
            purchase_cost = None
            if unit_price is not None:
                try:
                    purchase_cost = float(unit_price)
                except (TypeError, ValueError):
                    purchase_cost = None
            created_id = self._create_item(
                self.default_item_name,
                expense_account_id=expense_account_id,
                income_account_id=income_account_id,
                purchase_cost=purchase_cost,
                purchase_tax_code_id=str(taxcode_id).strip() if taxcode_id else None,
                purchase_tax_percent=tax_percent
            )
            if created_id:
                self.default_item_id = created_id
                key = self.default_item_name.strip().lower()
                self.item_cache[key] = created_id
                return str(created_id)
        return str(self.default_item_id) if self.default_item_id else None

    def _create_item(
        self,
        name: str,
        expense_account_id: Optional[str] = None,
        income_account_id: Optional[str] = None,
        purchase_cost: Optional[Any] = None,
        purchase_tax_code_id: Optional[Any] = None,
        purchase_tax_percent: Optional[Any] = None,
        sales_tax_code_id: Optional[Any] = None,
        sales_tax_percent: Optional[Any] = None
    ) -> Optional[str]:
        if not name:
            return None
        expense_account_id = expense_account_id or self._resolve_account_id('expense')
        income_account_id = income_account_id or self._resolve_account_id('income')
        if not income_account_id:
            logging.warning("[create_item] Nessun conto entrate valido identificato: impossibile creare l'articolo.")
            return None
        if not expense_account_id:
            logging.warning("[create_item] Nessun conto spese valido identificato: impossibile creare l'articolo.")
            return None
        purchase_tax_code_id = self._resolve_tax_code_id('purchase', purchase_tax_code_id, purchase_tax_percent)
        sales_tax_code_id = self._resolve_tax_code_id('sales', sales_tax_code_id, sales_tax_percent or purchase_tax_percent)
        payload: Dict[str, Any] = {
            "Name": name[:100],
            "Type": self.default_item_type or 'Service',
            "TrackQtyOnHand": False,
            "PurchaseDesc": name[:100],
            "Active": True
        }
        payload["ExpenseAccountRef"] = {"value": str(expense_account_id)}
        if purchase_cost is not None:
            try:
                payload["PurchaseCost"] = float(purchase_cost)
            except (TypeError, ValueError):
                pass
        payload["IncomeAccountRef"] = {"value": str(income_account_id)}
        if purchase_tax_code_id:
            payload["PurchaseTaxCodeRef"] = {"value": str(purchase_tax_code_id)}
        if sales_tax_code_id:
            payload["SalesTaxCodeRef"] = {"value": str(sales_tax_code_id)}
        url = f"{self.base_url}/v3/company/{self.realm_id}/item"
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code in (200, 201):
                data = response.json()
                item = data.get("Item")
                if item:
                    item_id = item.get("Id")
                    logging.info(f"[create_item] Articolo '{name}' creato con ID {item_id}")
                    return item_id
                logging.error(f"[create_item] Risposta senza Item: {data}")
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = response.text
                logging.error(f"[create_item] Errore {response.status_code}: {error_data}")
        except Exception as e:
            logging.error(f"[create_item] Errore nella creazione dell'articolo '{name}': {e}")
        return None

    def _resolve_account_id(self, kind: str) -> Optional[str]:
        if kind not in ("expense", "income"):
            return None
        id_attr = 'default_item_expense_account_id' if kind == 'expense' else 'default_item_income_account_id'
        name_attr = 'default_item_expense_account_name' if kind == 'expense' else 'default_item_income_account_name'
        fallback_types = [
            'Cost of Goods Sold',
            'CostOfGoodsSold',
            'Expense',
            'Other Expense',
            'OtherExpense'
        ] if kind == 'expense' else [
            'Income',
            'Other Income',
            'OtherIncome'
        ]
        current_id = getattr(self, id_attr, None)
        if current_id:
            return str(current_id)
        account_name = getattr(self, name_attr, None)
        if account_name:
            account_id = self._get_account_id_by_name(account_name)
            if account_id:
                setattr(self, id_attr, account_id)
                return str(account_id)
        account_id = self._find_account_id_by_type(fallback_types)
        if account_id:
            setattr(self, id_attr, account_id)
            return str(account_id)
        return None

    def _get_account_id_by_name(self, name: str) -> Optional[str]:
        if not name:
            return None
        key = f"name::{name.strip().lower()}"
        if key in self.account_cache:
            cached = self.account_cache[key]
            return str(cached) if cached else None
        account = self.get_account_by_name(name)
        if account:
            account_id = account.get('Id')
            self.account_cache[key] = account_id
            return str(account_id) if account_id else None
        self.account_cache[key] = None
        return None

    def _find_account_id_by_type(self, account_types: List[str]) -> Optional[str]:
        for account_type in account_types:
            if not account_type:
                continue
            key = f"type::{account_type.strip().lower()}"
            if key in self.account_cache:
                cached = self.account_cache[key]
                if cached:
                    return str(cached)
                continue
            account = self._get_first_account_by_type(account_type)
            if account:
                account_id = account.get('Id')
                self.account_cache[key] = account_id
                if account_id:
                    return str(account_id)
            else:
                self.account_cache[key] = None
        return None

    def _get_first_account_by_type(self, account_type: str) -> Optional[Dict[str, Any]]:
        if not account_type:
            return None
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        safe_type = account_type.replace("'", "\\'")
        query = (
            "SELECT Id, Name, AccountType FROM Account "
            f"WHERE AccountType = '{safe_type}' AND Active = true "
            "ORDER BY FullyQualifiedName ASC"
        )
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("QueryResponse", {}).get("Account", [])
                if isinstance(accounts, dict):
                    accounts = [accounts]
                if accounts:
                    return accounts[0]
            else:
                logging.error(f"[_get_first_account_by_type] Errore {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"[_get_first_account_by_type] Errore: {e}")
        return None

    def _resolve_tax_code_id(
        self,
        kind: str,
        prefer_id: Optional[Any] = None,
        fallback_percent: Optional[Any] = None
    ) -> Optional[str]:
        if kind not in ("purchase", "sales"):
            return None

        def normalize(value: Optional[Any]) -> Optional[str]:
            if value is None:
                return None
            if isinstance(value, str):
                value = value.strip()
            return str(value) if value else None

        attr = 'default_item_purchase_tax_code_id' if kind == 'purchase' else 'default_item_sales_tax_code_id'
        preferred = normalize(prefer_id)
        if preferred:
            setattr(self, attr, preferred)
            return preferred

        existing = normalize(getattr(self, attr, None))
        if existing:
            return existing

        percent = self._extract_percent_str(fallback_percent)
        self._ensure_tax_codes_loaded()
        candidates = self._tax_code_cache.get(kind, []) if isinstance(self._tax_code_cache, dict) else []
        if not candidates:
            return None

        if percent:
            for tax in candidates:
                text = f"{tax.get('Name', '')} {tax.get('Description', '')}"
                if percent in text:
                    selected = normalize(tax.get('Id'))
                    if selected:
                        setattr(self, attr, selected)
                        return selected

        keywords = ['Acquisti'] if kind == 'purchase' else ['Vendite', 'Sales']
        for tax in candidates:
            text_lower = f"{tax.get('Name', '')} {tax.get('Description', '')}".lower()
            if any(keyword.lower() in text_lower for keyword in keywords):
                selected = normalize(tax.get('Id'))
                if selected:
                    setattr(self, attr, selected)
                    return selected

        for tax in candidates:
            if tax.get('Taxable'):
                selected = normalize(tax.get('Id'))
                if selected:
                    setattr(self, attr, selected)
                    return selected

        for tax in candidates:
            selected = normalize(tax.get('Id'))
            if selected:
                setattr(self, attr, selected)
                return selected

        return None

    def _ensure_tax_codes_loaded(self) -> None:
        if self._tax_code_cache_loaded:
            return
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        query = (
            "SELECT Id, Name, Description, Active, Taxable, PurchaseTaxRateList, SalesTaxRateList "
            "FROM TaxCode WHERE Active = true"
        )
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                tax_codes = data.get("QueryResponse", {}).get("TaxCode", [])
                if isinstance(tax_codes, dict):
                    tax_codes = [tax_codes]
                purchase_codes = []
                sales_codes = []
                for tax in tax_codes:
                    if tax.get('PurchaseTaxRateList'):
                        purchase_codes.append(tax)
                    if tax.get('SalesTaxRateList'):
                        sales_codes.append(tax)
                self._tax_code_cache = {
                    'purchase': purchase_codes,
                    'sales': sales_codes,
                    'all': tax_codes
                }
            else:
                logging.error(f"[_ensure_tax_codes_loaded] Errore {response.status_code}: {response.text}")
                self._tax_code_cache = {}
        except Exception as e:
            logging.error(f"[_ensure_tax_codes_loaded] Errore: {e}")
            self._tax_code_cache = {}
        finally:
            self._tax_code_cache_loaded = True

    @staticmethod
    def _extract_percent_str(value: Optional[Any]) -> Optional[str]:
        if value is None:
            return None
        value_str = str(value).strip()
        if not value_str:
            return None
        match = re.search(r"\d+", value_str)
        return match.group(0) if match else None

    def get_item_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        safe_name = name.replace("'", "\\'")
        query = f"SELECT * FROM Item WHERE Name = '{safe_name}'"
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("QueryResponse", {}).get("Item", [])
                if items:
                    return items[0]
            else:
                logging.error(f"[get_item_by_name] Errore {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"[get_item_by_name] Errore: {e}")
        return None

    def get_account_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        safe_name = name.replace("'", "\\'")
        query = (
            "SELECT Id, Name, AccountType, AccountSubType FROM Account "
            f"WHERE Name = '{safe_name}' AND Active = true"
        )
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                accounts = data.get("QueryResponse", {}).get("Account", [])
                if isinstance(accounts, dict):
                    accounts = [accounts]
                if accounts:
                    return accounts[0]
            else:
                logging.error(f"[get_account_by_name] Errore {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"[get_account_by_name] Errore: {e}")
        return None

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

    def find_bill_by_docnumber(self, vendor_id: str, doc_number: str) -> Optional[Dict[str, Any]]:
        if not vendor_id or not doc_number:
            return None
        url = f"{self.base_url}/v3/company/{self.realm_id}/query"
        safe_doc = doc_number.replace("'", "\\'")
        query = (
            "SELECT Id, SyncToken, DocNumber FROM Bill "
            f"WHERE DocNumber = '{safe_doc}' AND VendorRef = '{vendor_id}' "
            "ORDER BY Metadata.LastUpdatedTime DESC"
        )
        params = {"query": query}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                bills = data.get("QueryResponse", {}).get("Bill", [])
                if isinstance(bills, dict):
                    bills = [bills]
                if bills:
                    bill = bills[0]
                    return {
                        "Id": bill.get("Id"),
                        "SyncToken": bill.get("SyncToken"),
                        "DocNumber": bill.get("DocNumber") or bill.get("DocNum"),
                        "Bill": bill
                    }
            else:
                logging.error(f"[find_bill_by_docnumber] Errore {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"[find_bill_by_docnumber] Errore: {e}")
        return None

    def update_bill(self, bill_id: str, sync_token: str, bill_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not bill_id or sync_token is None:
            return {"error": "Bill Id o SyncToken mancanti"}
        url = f"{self.base_url}/v3/company/{self.realm_id}/bill"
        payload = self._build_bill_payload(bill_data)
        payload["Id"] = str(bill_id)
        payload["SyncToken"] = str(sync_token)
        payload["sparse"] = False
        # 🔍 LOG PAYLOAD UPDATE PER DEBUG
        logging.info(f"[update_bill] PAYLOAD QuickBooks (update Bill {bill_id}):\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                bill_updated = result.get("Bill")
                if isinstance(bill_updated, list) and bill_updated:
                    bill_updated = bill_updated[0]
                if bill_updated:
                    logging.info(f"[update_bill] Fattura {bill_id} aggiornata con successo")
                    return result
                logging.error(f"[update_bill] Risposta senza dati Bill: {result}")
                return {"error": result}
            else:
                try:
                    error_data = response.json()
                except Exception:
                    error_data = response.text
                logging.error(f"[update_bill] Errore {response.status_code}: {error_data}")
                self._handle_error(response, "update_bill")
                return {"error": error_data, "status_code": response.status_code}
        except Exception as e:
            logging.error(f"[update_bill] Errore durante l'aggiornamento: {e}")
            return {"error": str(e)}

    def find_or_create_vendor(self, vendor_name: str, vendor_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
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
            # QuickBooks Online richiede l'apostrofo escapato come \\' nelle query
            safe_name = name.replace("'", "\\'" )
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
