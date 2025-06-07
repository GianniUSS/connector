# quickbooks_taxcode_cache.py
import threading
from get_quickbooks_taxcodes import get_quickbooks_taxcodes

_taxcode_map = None
_taxcode_lock = threading.Lock()

def load_taxcode_cache(force_reload=False):
    global _taxcode_map
    with _taxcode_lock:
        if _taxcode_map is not None and not force_reload:
            return _taxcode_map
        taxcodes = get_quickbooks_taxcodes() or []
        # Mappa: percentuale (es. "22") -> ID
        _taxcode_map = {}
        for t in taxcodes:
            descr = t.get('Description', '')
            import re
            m = re.search(r'(\d+)%', descr)
            if m:
                percent = m.group(1)
                _taxcode_map[percent] = t.get('Id')
        return _taxcode_map

def get_taxcode_id(percent):
    cache = load_taxcode_cache()
    return cache.get(str(percent))
