import regex as re
from typing import Dict, Any, List, Tuple
_UNIT_MAP = {
    'kwh': ('energy', 1.0), 'mwh': ('energy', 1000.0), 'wh': ('energy', 0.001), 'gwh': ('energy', 1000000.0),
    'kw': ('power', 1.0), 'mw': ('power', 1000.0), 'kva': ('apparent_power', 1.0), 'mva': ('apparent_power', 1000.0),
    'kvar': ('reactive_power', 1.0), 'mvar': ('reactive_power', 1000.0), 'kvarh': ('reactive_energy', 1.0),
    'mvarh': ('reactive_energy', 1000.0), 'kwp': ('power_peak', 1.0)
}
_NUM = r'(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d+)?'
_UNITS = r'(?:kWh|MWh|Wh|GWh|kW|MW|kVA|MVA|kVAr|MVAr|kVArh|MVArh|kWp)'
PATTERN = re.compile(rf'(?P<num>{_NUM})\s*(?P<unit>{_UNITS})', re.IGNORECASE)
def _to_float(s: str) -> float:
    s = s.replace(' ', '')
    if s.count(',')>0 and s.count('.')>0: s = s.replace('.','').replace(',', '.')
    elif ',' in s and '.' not in s: s = s.replace(',', '.')
    else: s = s.replace(',', '')
    try: return float(s)
    except ValueError: return None
def extract_energy_values(text: str) -> Dict[str, Any]:
    found: List[Tuple[str, str, float]] = []
    for m in PATTERN.finditer(text):
        n = _to_float(m.group('num')); u = m.group('unit').lower()
        if n is None: continue
        kind, factor = _UNIT_MAP.get(u, (None, None))
        if kind is None: continue
        found.append((kind, u, n*factor))
    summary = {
        'energy_kwh':[v for (k,u,v) in found if k=='energy'],
        'power_kw':[v for (k,u,v) in found if k=='power'],
        'apparent_power_kva':[v for (k,u,v) in found if k=='apparent_power'],
        'reactive_power_kvar':[v for (k,u,v) in found if k=='reactive_power'],
        'reactive_energy_kvarh':[v for (k,u,v) in found if k=='reactive_energy'],
        'power_peak_kwp':[v for (k,u,v) in found if k=='power_peak'],
    }
    totals = {'total_energy_kwh': sum(summary['energy_kwh']) if summary['energy_kwh'] else 0.0}
    return {'items': found, 'summary': summary, 'totals': totals}
