#!/usr/bin/env python3
"""
Sistema di tracciamento unificato per importazioni QuickBooks
Gestisce lo stato di importazione di:
- Fatture (invoices)
- Ore (time_activities)
- Altre operazioni future
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional, List, Union
import logging

class QBTracker:
    """Sistema centralizzato per tracciare le operazioni QuickBooks"""
    
    def __init__(self, base_path=None):
        self.base_path = base_path or os.path.dirname(__file__)
        
        # File di tracciamento separati per tipologia
        self.files = {
            'invoices': os.path.join(self.base_path, 'qb_invoices_status.json'),
            'time_activities': os.path.join(self.base_path, 'qb_time_activities_status.json'),
            'general': os.path.join(self.base_path, 'qb_import_status.json')  # Compatibilità
        }
        
        # Lock per thread-safety
        self._locks = {
            'invoices': threading.Lock(),
            'time_activities': threading.Lock(),
            'general': threading.Lock()
        }
        
        logging.info("QBTracker inizializzato")
    
    def _load_status(self, operation_type: str) -> Dict:
        """Carica lo stato per un tipo di operazione"""
        file_path = self.files.get(operation_type)
        if not file_path:
            raise ValueError(f"Tipo operazione non supportato: {operation_type}")
        
        lock = self._locks[operation_type]
        
        with lock:
            if not os.path.exists(file_path):
                return {}
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Errore caricamento {operation_type}: {e}")
                return {}
    
    def _save_status(self, operation_type: str, status_dict: Dict) -> bool:
        """Salva lo stato per un tipo di operazione"""
        file_path = self.files.get(operation_type)
        if not file_path:
            raise ValueError(f"Tipo operazione non supportato: {operation_type}")
        
        lock = self._locks[operation_type]
        
        with lock:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(status_dict, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                logging.error(f"Errore salvataggio {operation_type}: {e}")
                return False
    
    def set_invoice_status(self, project_id: Union[str, int], status: str, message: str = None, details: Dict = None):
        """Traccia lo stato di importazione fattura per un progetto"""
        details = details or {}
        details.update({
            'project_id': str(project_id),
            'operation_type': 'invoice'
        })
        
        return self._set_status('invoices', project_id, status, message, details)
    
    def set_excel_import_status(self, import_type: str, key: Union[str, int], status: str, 
                               message: str = None, details: Dict = None):
        """Traccia lo stato di importazione da Excel (ore, fatture, etc.)"""
        excel_type = f"excel_{import_type}"
        
        # Crea il file di tracciamento se non esiste
        if excel_type not in self.files:
            self.files[excel_type] = os.path.join(self.base_path, f'qb_{excel_type}_status.json')
            self._locks[excel_type] = threading.Lock()
        
        details = details or {}
        details.update({
            'operation_type': excel_type,
            'import_source': 'excel'
        })
        
        return self._set_status(excel_type, key, status, message, details)
    
    def set_time_activity_status(self, project_id: Union[str, int], employee_name: str, status: str, 
                                message: str = None, details: Dict = None):
        """Traccia lo stato di importazione ore per un progetto/employee"""
        # Per le ore usiamo una chiave composta: project_id:employee_name
        key = f"{project_id}:{employee_name}"
        
        details = details or {}
        details.update({
            'project_id': str(project_id),
            'employee_name': employee_name,
            'operation_type': 'time_activity'
        })
        
        return self._set_status('time_activities', key, status, message, details)
    
    def set_deletion_status(self, operation_type: str, key_or_id: Union[str, int], status: str, 
                           message: str = None, details: Dict = None):
        """Traccia lo stato di eliminazione (ore, fatture, etc.)"""
        deletion_type = f"{operation_type}_deletions"
        
        # Crea il file di tracciamento se non esiste
        if deletion_type not in self.files:
            self.files[deletion_type] = os.path.join(self.base_path, f'qb_{deletion_type}_status.json')
            self._locks[deletion_type] = threading.Lock()
        
        details = details or {}
        details.update({
            'operation_type': deletion_type,
            'original_key': str(key_or_id)
        })
        
        return self._set_status(deletion_type, key_or_id, status, message, details)
    
    def set_general_status(self, project_id: Union[str, int], status: str, message: str = None, details: Dict = None):
        """Traccia stato generale (compatibilità con sistema esistente)"""
        return self._set_status('general', project_id, status, message, details)
    
    def _set_status(self, operation_type: str, key: Union[str, int], status: str, 
                   message: str = None, details: Dict = None):
        """Metodo interno per impostare lo stato"""
        status_dict = self._load_status(operation_type)
        
        status_data = {
            'status': status,
            'message': message or '',
            'timestamp': datetime.now().isoformat(timespec='seconds'),
            'details': details or {}
        }
        
        status_dict[str(key)] = status_data
        
        success = self._save_status(operation_type, status_dict)
        if success:
            logging.info(f"Aggiornato stato {operation_type} per {key}: {status}")
        
        return success
    
    def get_invoice_status(self, project_id: Union[str, int]) -> Optional[Dict]:
        """Recupera lo stato di importazione fattura"""
        return self._get_status('invoices', project_id)
    
    def get_time_activity_status(self, project_id: Union[str, int], employee_name: str) -> Optional[Dict]:
        """Recupera lo stato di importazione ore per project/employee"""
        key = f"{project_id}:{employee_name}"
        return self._get_status('time_activities', key)
    
    def get_excel_import_status(self, import_type: str, key: Union[str, int]) -> Optional[Dict]:
        """Recupera lo stato di importazione Excel"""
        excel_type = f"excel_{import_type}"
        return self._get_status(excel_type, key)
    
    def get_all_excel_imports(self, import_type: str) -> Dict:
        """Recupera tutte le importazioni Excel per un tipo"""
        excel_type = f"excel_{import_type}"
        return self._load_status(excel_type)
    
    def get_deletion_status(self, operation_type: str, key_or_id: Union[str, int]) -> Optional[Dict]:
        """Recupera lo stato di eliminazione"""
        deletion_type = f"{operation_type}_deletions"
        return self._get_status(deletion_type, key_or_id)
    
    def get_all_deletions(self, operation_type: str) -> Dict:
        """Recupera tutte le eliminazioni per un tipo di operazione"""
        deletion_type = f"{operation_type}_deletions"
        return self._load_status(deletion_type)
    
    def get_general_status(self, project_id: Union[str, int]) -> Optional[Dict]:
        """Recupera stato generale (compatibilità)"""
        return self._get_status('general', project_id)
    
    def _get_status(self, operation_type: str, key: Union[str, int]) -> Optional[Dict]:
        """Metodo interno per recuperare lo stato"""
        status_dict = self._load_status(operation_type)
        return status_dict.get(str(key))
    
    def get_project_time_activities(self, project_id: Union[str, int]) -> List[Dict]:
        """Recupera tutte le ore importate per un progetto"""
        status_dict = self._load_status('time_activities')
        project_activities = []
        
        project_str = str(project_id)
        for key, data in status_dict.items():
            if key.startswith(f"{project_str}:"):
                employee_name = key.split(':', 1)[1]
                activity_info = data.copy()
                activity_info['employee_name'] = employee_name
                activity_info['project_id'] = project_str
                project_activities.append(activity_info)
        
        return project_activities
    
    def get_project_summary(self, project_id: Union[str, int]) -> Dict:
        """Recupera un riassunto completo delle operazioni per un progetto"""
        project_str = str(project_id)
        
        summary = {
            'project_id': project_str,
            'invoice': self.get_invoice_status(project_id),
            'time_activities': self.get_project_time_activities(project_id),
            'excel_imports': {
                'hours': self.get_excel_import_status('hours', project_id),
                'invoices': self.get_excel_import_status('invoices', project_id)
            },
            'general': self.get_general_status(project_id)
        }
        
        return summary
    
    def get_statistics(self, operation_type: str = None) -> Dict:
        """Recupera statistiche sulle operazioni"""
        if operation_type:
            return self._get_operation_statistics(operation_type)
        
        # Statistiche globali
        stats = {}
        for op_type in self.files.keys():
            stats[op_type] = self._get_operation_statistics(op_type)
        
        return stats
    
    def _get_operation_statistics(self, operation_type: str) -> Dict:
        """Statistiche per un tipo di operazione"""
        status_dict = self._load_status(operation_type)
        
        if not status_dict:
            return {'total': 0, 'success': 0, 'error': 0, 'other': 0}
        
        stats = {'total': len(status_dict), 'success': 0, 'error': 0, 'timeout': 0, 'other': 0}
        
        for data in status_dict.values():
            status = data.get('status', 'unknown')
            if status in ['success', 'success_simulated']:
                stats['success'] += 1
            elif status == 'error':
                stats['error'] += 1
            elif status == 'timeout':
                stats['timeout'] += 1
            else:
                stats['other'] += 1
        
        return stats
    
    def cleanup_old_entries(self, operation_type: str, days_old: int = 30):
        """Rimuove entry più vecchie di N giorni"""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        status_dict = self._load_status(operation_type)
        
        if not status_dict:
            return 0
        
        removed_count = 0
        keys_to_remove = []
        
        for key, data in status_dict.items():
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp < cutoff_date:
                        keys_to_remove.append(key)
                except ValueError:
                    continue
        
        for key in keys_to_remove:
            del status_dict[key]
            removed_count += 1
        
        if removed_count > 0:
            self._save_status(operation_type, status_dict)
            logging.info(f"Rimossi {removed_count} entry vecchi da {operation_type}")
        
        return removed_count
    
    def export_to_csv(self, operation_type: str, output_file: str = None) -> str:
        """Esporta i dati in formato CSV"""
        import csv
        
        status_dict = self._load_status(operation_type)
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"qb_{operation_type}_export_{timestamp}.csv"
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if not status_dict:
                return output_file
            
            # Estrai i campi dalla prima entry
            first_entry = next(iter(status_dict.values()))
            fieldnames = ['key', 'status', 'message', 'timestamp']
            
            # Aggiungi campi dai details se presenti
            if 'details' in first_entry:
                for detail_key in first_entry['details'].keys():
                    if detail_key not in fieldnames:
                        fieldnames.append(detail_key)
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for key, data in status_dict.items():
                row = {
                    'key': key,
                    'status': data.get('status', ''),
                    'message': data.get('message', ''),
                    'timestamp': data.get('timestamp', '')
                }
                
                # Aggiungi details se presenti
                if 'details' in data:
                    row.update(data['details'])
                
                writer.writerow(row)
        
        logging.info(f"Esportati dati {operation_type} in {output_file}")
        return output_file

# Istanza globale del tracker
qb_tracker = QBTracker()

# Funzioni di compatibilità con il sistema esistente
def set_qb_import_status(project_id: Union[str, int], status: str, message: str = None):
    """Compatibilità con sistema esistente"""
    return qb_tracker.set_general_status(project_id, status, message)

def get_qb_import_status(project_id: Union[str, int]) -> Optional[Dict]:
    """Compatibilità con sistema esistente"""
    return qb_tracker.get_general_status(project_id)

def load_qb_import_status() -> Dict:
    """Compatibilità con sistema esistente"""
    return qb_tracker._load_status('general')

def save_qb_import_status(status_dict: Dict) -> bool:
    """Compatibilità con sistema esistente"""
    return qb_tracker._save_status('general', status_dict)
