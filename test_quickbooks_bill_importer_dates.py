import unittest
from quickbooks_bill_importer import QuickBooksBillImporter
from datetime import datetime
import os

class TestQuickBooksBillImporterDates(unittest.TestCase):
    def setUp(self):
        # Usa variabili d'ambiente o valori fittizi per test locali
        self.base_url = os.environ.get("QB_BASE_URL", "https://quickbooks.api.intuit.com")
        self.realm_id = os.environ.get("QB_REALM_ID", "1234567890")
        self.access_token = os.environ.get("QB_ACCESS_TOKEN", "test-token")
        self.importer = QuickBooksBillImporter(self.base_url, self.realm_id, self.access_token)

    def test_date_normalization(self):
        bill_data = {
            'vendor_id': '1008',
            'txn_date': '31/10/2024',  # formato DD/MM/YYYY
            'due_date': '30/11/2024',  # formato DD/MM/YYYY
            'total_amount': 6.48,
            'line_items': [
                {
                    'amount': 6.48,
                    'account_id': '1',
                    'description': 'Google Workspace'
                }
            ],
            'ref_number': 'GCITD0003889579',
            'memo': 'Test fattura con date in formato europeo'
        }
        payload = self.importer._build_bill_payload(bill_data)
        # Le date devono essere normalizzate in YYYY-MM-DD
        self.assertEqual(payload['TxnDate'], '2024-10-31')
        self.assertEqual(payload['DueDate'], '2024-11-30')
        # La validazione deve passare
        self.assertTrue(self.importer._validate_bill_payload(payload))

if __name__ == "__main__":
    unittest.main()
