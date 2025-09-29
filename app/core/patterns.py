import regex as re
from typing import Dict, Any, List
import phonenumbers
CEDULA = re.compile(r'\b\d{10}\b')
RUC = re.compile(r'\b\d{13}\b')
EMAIL = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.I)
USD_AMOUNT = re.compile(r'\$\s*(\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d+)?')
def extract_basic_patterns(text: str, region_code: str = 'EC') -> Dict[str, Any]:
    cedulas = list(set(CEDULA.findall(text))); rucs = list(set(RUC.findall(text)))
    emails = list(set(EMAIL.findall(text))); usd_vals = USD_AMOUNT.findall(text)
    phones: List[str] = []
    for m in phonenumbers.PhoneNumberMatcher(text, region_code):
        try:
            e164 = phonenumbers.format_number(m.number, phonenumbers.PhoneNumberFormat.E164)
            if e164 not in phones: phones.append(e164)
        except Exception: pass
    return {'cedulas': cedulas, 'rucs': rucs, 'emails': emails, 'phones': phones, 'usd_amounts': usd_vals}
