import requests
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import config

class RentmanAPIExplorer:
    """Esplora gli endpoint API di Rentman per mappare la struttura"""
    
    def __init__(self):
        self.base_url = config.REN_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {config.REN_API_TOKEN}',
            'Accept': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.discovered_endpoints = {}
    
    def explore_equipment_endpoints(self) -> Dict:
        """Esplora tutti gli endpoint relativi a equipment e stock"""
        
        print("🔍 RENTMAN API EXPLORER - EQUIPMENT & STOCK")
        print("=" * 60)
        
        # Lista endpoint da testare
        endpoints_to_test = [
            # Equipment core
            'equipment',
            'projectequipment', 
            'equipmentgroups',
            'equipmentsets',
            'equipmentcategories',
            
            # Stock e inventory
            'stock',
            'stockmovements',
            'stocklocations',
            'inventory',
            'warehouses',
            
            # Shortages e planning
            'shortages',
            'reservations',
            'bookings',
            'planning',
            'availability',
            
            # Altri possibili
            'serialnumbers',
            'repairs',
            'transfers',
            'subrentals',
            'alternatives'
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            print(f"\n🧪 Testing /{endpoint}...")
            
            try:
                result = self._test_endpoint(endpoint)
                if result['status'] == 'success':
                    print(f"   ✅ FOUND: /{endpoint}")
                    print(f"   📊 Items: {result.get('item_count', 'N/A')}")
                    
                    # Mostra sample dei campi
                    sample_fields = result.get('sample_fields', [])
                    if sample_fields:
                        print(f"   📋 Fields: {', '.join(sample_fields[:8])}{'...' if len(sample_fields) > 8 else ''}")
                else:
                    print(f"   ❌ Not found: {result.get('error', 'Unknown error')}")
                
                results[endpoint] = result
                
            except Exception as e:
                print(f"   💥 Error testing /{endpoint}: {e}")
                results[endpoint] = {'status': 'error', 'error': str(e)}
        
        self.discovered_endpoints = results
        return results
    
    def _test_endpoint(self, endpoint: str) -> Dict:
        """Testa un singolo endpoint"""
        
        try:
            # Test con paginazione piccola per velocità
            params = {'limit': 5, 'offset': 0}
            
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                params=params,
                timeout=10
            )
            
            if response.ok:
                data = response.json()
                
                # Analizza struttura risposta
                items = data.get('data', [])
                item_count = data.get('itemCount', len(items))
                
                # Estrai campi da sample item
                sample_fields = []
                if items and len(items) > 0:
                    sample_item = items[0]
                    sample_fields = list(sample_item.keys()) if isinstance(sample_item, dict) else []
                
                return {
                    'status': 'success',
                    'endpoint': endpoint,
                    'http_status': response.status_code,
                    'item_count': item_count,
                    'sample_fields': sample_fields,
                    'sample_data': items[0] if items else None,
                    'full_response_structure': {
                        'has_data_field': 'data' in data,
                        'has_itemCount': 'itemCount' in data,
                        'has_limit': 'limit' in data,
                        'has_offset': 'offset' in data,
                        'top_level_keys': list(data.keys())
                    }
                }
            else:
                return {
                    'status': 'failed',
                    'endpoint': endpoint,
                    'http_status': response.status_code,
                    'error': f"HTTP {response.status_code}"
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'endpoint': endpoint,
                'error': str(e)
            }
    
    def analyze_equipment_structure(self) -> Dict:
        """Analizza la struttura dei dati equipment trovati"""
        
        if not self.discovered_endpoints:
            print("❌ Esegui prima explore_equipment_endpoints()")
            return {}
        
        print(f"\n📊 ANALISI STRUTTURA EQUIPMENT")
        print("=" * 50)
        
        analysis = {
            'successful_endpoints': [],
            'equipment_related': {},
            'stock_related': {},
            'project_related': {},
            'shortage_indicators': []
        }
        
        for endpoint, result in self.discovered_endpoints.items():
            if result.get('status') == 'success':
                analysis['successful_endpoints'].append(endpoint)
                
                sample_fields = result.get('sample_fields', [])
                
                # Categorizza endpoint
                if any(keyword in endpoint.lower() for keyword in ['equipment', 'serial']):
                    analysis['equipment_related'][endpoint] = {
                        'fields': sample_fields,
                        'count': result.get('item_count', 0)
                    }
                
                elif any(keyword in endpoint.lower() for keyword in ['stock', 'inventory', 'warehouse']):
                    analysis['stock_related'][endpoint] = {
                        'fields': sample_fields,
                        'count': result.get('item_count', 0)
                    }
                
                elif any(keyword in endpoint.lower() for keyword in ['project', 'planning', 'booking']):
                    analysis['project_related'][endpoint] = {
                        'fields': sample_fields,
                        'count': result.get('item_count', 0)
                    }
                
                # Cerca indicatori di carenza
                shortage_indicators = []
                for field in sample_fields:
                    if any(keyword in field.lower() for keyword in ['shortage', 'available', 'reserved', 'planned', 'quantity']):
                        shortage_indicators.append(field)
                
                if shortage_indicators:
                    analysis['shortage_indicators'].extend([
                        f"{endpoint}: {', '.join(shortage_indicators)}"
                    ])
        
        self._print_analysis(analysis)
        return analysis
    
    def _print_analysis(self, analysis: Dict):
        """Stampa l'analisi in formato leggibile"""
        
        print(f"✅ Endpoint funzionanti: {len(analysis['successful_endpoints'])}")
        
        # Equipment endpoints
        if analysis['equipment_related']:
            print(f"\n🔧 EQUIPMENT ENDPOINTS:")
            for endpoint, info in analysis['equipment_related'].items():
                print(f"   /{endpoint} ({info['count']} items)")
                key_fields = [f for f in info['fields'][:6]]
                print(f"      Fields: {', '.join(key_fields)}")
        
        # Stock endpoints  
        if analysis['stock_related']:
            print(f"\n📦 STOCK ENDPOINTS:")
            for endpoint, info in analysis['stock_related'].items():
                print(f"   /{endpoint} ({info['count']} items)")
                key_fields = [f for f in info['fields'][:6]]
                print(f"      Fields: {', '.join(key_fields)}")
        
        # Project endpoints
        if analysis['project_related']:
            print(f"\n📋 PROJECT ENDPOINTS:")
            for endpoint, info in analysis['project_related'].items():
                print(f"   /{endpoint} ({info['count']} items)")
                key_fields = [f for f in info['fields'][:6]]
                print(f"      Fields: {', '.join(key_fields)}")
        
        # Shortage indicators
        if analysis['shortage_indicators']:
            print(f"\n🎯 POSSIBILI CAMPI PER CARENZE:")
            for indicator in analysis['shortage_indicators']:
                print(f"   {indicator}")
    
    def deep_dive_endpoint(self, endpoint: str, limit: int = 10) -> Dict:
        """Analisi approfondita di un endpoint specifico"""
        
        print(f"\n🔬 DEEP DIVE: /{endpoint}")
        print("=" * 40)
        
        try:
            response = self.session.get(
                f"{self.base_url}/{endpoint}",
                params={'limit': limit, 'offset': 0},
                timeout=15
            )
            
            if not response.ok:
                print(f"❌ Errore: HTTP {response.status_code}")
                return {}
            
            data = response.json()
            items = data.get('data', [])
            
            if not items:
                print("❌ Nessun dato trovato")
                return {}
            
            # Analizza tutti i campi
            all_fields = set()
            field_types = {}
            field_samples = {}
            
            for item in items:
                if isinstance(item, dict):
                    for field, value in item.items():
                        all_fields.add(field)
                        
                        # Tipo del campo
                        field_type = type(value).__name__
                        if field not in field_types:
                            field_types[field] = set()
                        field_types[field].add(field_type)
                        
                        # Sample value
                        if field not in field_samples and value is not None:
                            field_samples[field] = str(value)[:50]
            
            # Stampa analisi
            print(f"📊 Totale items: {len(items)}")
            print(f"📋 Campi trovati: {len(all_fields)}")
            print(f"\n🔍 STRUTTURA CAMPI:")
            
            for field in sorted(all_fields):
                types = ', '.join(field_types.get(field, ['unknown']))
                sample = field_samples.get(field, 'N/A')
                print(f"   {field:25} | {types:15} | {sample}")
            
            # Cerca pattern interessanti
            self._analyze_field_patterns(all_fields, field_samples)
            
            return {
                'endpoint': endpoint,
                'total_items': len(items),
                'fields': list(all_fields),
                'field_types': {k: list(v) for k, v in field_types.items()},
                'field_samples': field_samples,
                'sample_items': items[:3]
            }
            
        except Exception as e:
            print(f"💥 Errore: {e}")
            return {}
    
    def _analyze_field_patterns(self, fields: set, samples: Dict):
        """Analizza pattern nei campi per identificare funzionalità"""
        
        patterns = {
            'quantity_fields': [f for f in fields if 'quantity' in f.lower() or 'amount' in f.lower()],
            'date_fields': [f for f in fields if 'date' in f.lower() or 'time' in f.lower() or f.endswith('_start') or f.endswith('_end')],
            'reference_fields': [f for f in fields if samples.get(f, '').startswith('/') if f in samples],
            'status_fields': [f for f in fields if 'status' in f.lower() or 'state' in f.lower()],
            'id_fields': [f for f in fields if f.endswith('_id') or f == 'id']
        }
        
        print(f"\n🎯 PATTERN IDENTIFICATI:")
        for pattern_name, pattern_fields in patterns.items():
            if pattern_fields:
                print(f"   {pattern_name}: {', '.join(pattern_fields[:5])}")
    
    def suggest_shortage_strategy(self) -> Dict:
        """Suggerisce strategia per calcolare carenze basata sui dati trovati"""
        
        if not self.discovered_endpoints:
            print("❌ Esegui prima explore_equipment_endpoints()")
            return {}
        
        print(f"\n💡 STRATEGIA SUGGERITA PER CARENZE")
        print("=" * 45)
        
        # Analizza endpoint disponibili
        available = [ep for ep, result in self.discovered_endpoints.items() 
                    if result.get('status') == 'success']
        
        strategy = {
            'recommended_approach': 'unknown',
            'required_endpoints': [],
            'steps': [],
            'limitations': []
        }
        
        if 'equipment' in available and 'projectequipment' in available:
            strategy['recommended_approach'] = 'project_equipment_analysis'
            strategy['required_endpoints'] = ['equipment', 'projectequipment']
            strategy['steps'] = [
                "1. Recupera tutti gli equipment dal catalogo (/equipment)",
                "2. Per ogni progetto, recupera equipment pianificato (/projectequipment)", 
                "3. Calcola totale equipment pianificato per periodo",
                "4. Confronta con stock disponibile per identificare carenze"
            ]
        
        elif 'stockmovements' in available:
            strategy['recommended_approach'] = 'stock_movements_analysis'
            strategy['required_endpoints'] = ['stockmovements', 'projects']
            strategy['steps'] = [
                "1. Analizza movimenti stock (/stockmovements)",
                "2. Calcola stock attuale per equipment",
                "3. Recupera progetti e deduce equipment necessario",
                "4. Confronta disponibilità vs necessità"
            ]
            strategy['limitations'] = [
                "Richiede calcoli complessi sui movimenti",
                "Potrebbe non avere info dirette su planning"
            ]
        
        else:
            strategy['recommended_approach'] = 'indirect_analysis'
            strategy['steps'] = [
                "Analizza progetti per identificare pattern di carenza",
                "Usa indicatori indiretti (status, flag, etc.)"
            ]
            strategy['limitations'] = [
                "Approccio indiretto, meno preciso",
                "Dipende da flag/status nei progetti"
            ]
        
        # Stampa strategia
        print(f"🎯 Approccio: {strategy['recommended_approach']}")
        print(f"📋 Endpoint necessari: {', '.join(strategy['required_endpoints'])}")
        print(f"\n📝 PASSI:")
        for step in strategy['steps']:
            print(f"   {step}")
        
        if strategy['limitations']:
            print(f"\n⚠️ LIMITAZIONI:")
            for limit in strategy['limitations']:
                print(f"   - {limit}")
        
        return strategy
    
    def export_exploration_report(self, filename: str = None):
        """Esporta report dell'esplorazione"""
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"rentman_api_exploration_{timestamp}.json"
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'discovered_endpoints': self.discovered_endpoints,
            'analysis': self.analyze_equipment_structure() if self.discovered_endpoints else {},
            'exploration_summary': {
                'total_tested': len(self.discovered_endpoints),
                'successful': len([r for r in self.discovered_endpoints.values() if r.get('status') == 'success']),
                'failed': len([r for r in self.discovered_endpoints.values() if r.get('status') == 'failed']),
                'errors': len([r for r in self.discovered_endpoints.values() if r.get('status') == 'error'])
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"📄 Report esportato: {filename}")
            
        except Exception as e:
            print(f"❌ Errore export: {e}")


def main():
    """Demo dell'API Explorer"""
    
    print("🔍 RENTMAN API EXPLORER")
    print("=" * 40)
    
    explorer = RentmanAPIExplorer()
    
    # Step 1: Esplora endpoint equipment
    print("\n🚀 FASE 1: Esplorazione endpoint...")
    results = explorer.explore_equipment_endpoints()
    
    # Step 2: Analizza struttura
    print("\n🚀 FASE 2: Analisi struttura...")
    analysis = explorer.analyze_equipment_structure()
    
    # Step 3: Suggerisci strategia
    print("\n🚀 FASE 3: Strategia carenze...")
    strategy = explorer.suggest_shortage_strategy()
    
    # Step 4: Deep dive su endpoint interessanti
    successful_endpoints = [ep for ep, result in results.items() 
                          if result.get('status') == 'success']
    
    if successful_endpoints:
        print(f"\n🚀 FASE 4: Deep dive...")
        
        # Priorità: equipment, projectequipment, stockmovements
        priority_endpoints = ['equipment', 'projectequipment', 'stockmovements']
        
        for endpoint in priority_endpoints:
            if endpoint in successful_endpoints:
                print(f"\n" + "="*60)
                explorer.deep_dive_endpoint(endpoint, limit=5)
                break
    
    # Step 5: Export report
    print(f"\n🚀 FASE 5: Export report...")
    explorer.export_exploration_report()
    
    print(f"\n✅ Esplorazione completata!")
    return explorer


if __name__ == "__main__":
    explorer = main()