from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

# --- Utiles de normalizacion
def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

# --- Cedula (Ecuador, 10 digitos) ---
def _cedula_valida(ced: str) -> bool:
    if not re.fullmatch(r"\d{10}", ced):
        return False
    prov = int(ced[0:2])
    if not (1 <= prov <= 24 or prov == 30):  # permitir 30 (migracion)
        return False
    coef = [2,1,2,1,2,1,2,1,2]
    suma = 0
    for i in range(9):
        x = int(ced[i]) * coef[i]
        if x > 9:
            x -= 9
        suma += x
    dv = (10 - (suma % 10)) % 10
    return dv == int(ced[9])

def find_cedulas(text: str) -> List[str]:
    cands = set()
    for m in re.finditer(r"(?<!\d)(\d{10})(?!\d)", text):
        ced = m.group(1)
        if _cedula_valida(ced):
            cands.add(ced)
    return sorted(cands)

# --- RUC (13 digitos, validacion basica) ---
def _ruc_valido(ruc: str) -> bool:
    if not re.fullmatch(r"\d{13}", ruc):
        return False
    prov = int(ruc[0:2])
    if not (1 <= prov <= 24 or prov == 30):
        return False
    ter = int(ruc[2])
    ult3 = int(ruc[10:13])
    if ult3 == 0:
        return False
    # naturales: ter <= 5 y los primeros 10 deben ser c?dula v?lida
    if ter <= 5:
        return _cedula_valida(ruc[:10])
    # publico 6, privado 9 -> validacion simple: aceptamos estructura
    return ter in (6,9)

def find_rucs(text: str) -> List[str]:
    cands = set()
    for m in re.finditer(r"(?<!\d)(\d{13})(?!\d)", text):
        r = m.group(1)
        if _ruc_valido(r):
            cands.add(r)
    return sorted(cands)

# --- Fechas ---
_MESES = {
    "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
    "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12
}

def _fecha_iso(y:int,m:int,d:int) -> str:
    try:
        return f"{y:04d}-{m:02d}-{d:02d}"
    except Exception:
        return ""

def find_fechas(text: str) -> List[str]:
    out = set()
    t = text

    # dd/mm/yyyy o dd-mm-yyyy
    for m in re.finditer(r"\b(0?[1-9]|[12]\d|3[01])[\/\-](0?[1-9]|1[0-2])[\/\-](\d{4})\b", t):
        d = int(m.group(1)); mo = int(m.group(2)); y = int(m.group(3))
        out.add(_fecha_iso(y,mo,d))
    # yyyy-mm-dd
    for m in re.finditer(r"\b(\d{4})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b", t):
        y = int(m.group(1)); mo = int(m.group(2)); d = int(m.group(3))
        out.add(_fecha_iso(y,mo,d))
    # "dd de MES de yyyy"
    for m in re.finditer(r"\b(0?[1-9]|[12]\d|3[01])\s+de\s+([A-Za-z??????]+)\s+de\s+(\d{4})", t, flags=re.IGNORECASE):
        d = int(m.group(1)); mes = m.group(2).lower()
        y = int(m.group(3)); mo = _MESES.get(mes, 0)
        if mo:
            out.add(_fecha_iso(y,mo,d))
    return sorted(out)

# --- Energia ---
def find_energia(text: str) -> List[Dict[str,str]]:
    # Captura valores con unidades t?picas
    out = []
    pat = re.compile(r"(\d[\d\.,]{0,12})\s*(kwh|kw|mwh|mw|wh|v|a)\b", re.IGNORECASE)
    for m in pat.finditer(text):
        val = m.group(1).replace(".", "").replace(",", ".")
        try:
            _ = float(val)
        except Exception:
            continue
        out.append({"valor": val, "unidad": m.group(2)})
    return out[:25]  # limitar

# --- Nombres (probables) ---
_STOP = set("DE DEL LA LOS LAS Y EN EL AL PARA POR CON A O U".split())
def find_nombres_probables(text: str, max_items:int = 10) -> List[str]:
    cands = {}
    for m in re.finditer(r"\b([A-Z??????]{2,}(?:\s+[A-Z??????]{2,}){1,3})\b", text):
        chunk = m.group(1)
        toks = chunk.split()
        if any(t in _STOP for t in toks):
            continue
        if len(toks) >= 2:
            cands[chunk] = cands.get(chunk, 0) + 1
    return [k for k,_ in sorted(cands.items(), key=lambda kv: (-kv[1], kv[0]))[:max_items]]

def extract_entities(text: str) -> Dict[str, Any]:
    return {
        "cedulas": find_cedulas(text),
        "rucs": find_rucs(text),
        "fechas": find_fechas(text),
        "energia": find_energia(text),
        "nombres_probables": find_nombres_probables(text),
        "texto_len": len(text or "")
    }
