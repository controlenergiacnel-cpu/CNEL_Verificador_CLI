from __future__ import annotations
import os, argparse, json, unicodedata
from typing import List, Dict, Any, Tuple
from app.core.pdf_text import extract_text_with_meta
from app.core.director import find_director_mentions
from app.core.signatures_robust import extract_signatures
from app.core.extractors import extract_entities

SEP = "=" * 78
SUB = "-" * 78

def _load_cfg() -> Dict[str, Any]:
    p = os.path.join("config","config.json")
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as fh:
            return json.load(fh)
    except Exception:
        return {}

# -------- ASCII safe output (opcional) ----------
def _to_ascii(s: str) -> str:
    if not s:
        return ""
    # normaliza acentos -> ascii
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    # limpia espacios
    return " ".join(s.split())

def _out(s: str, ascii_mode: bool) -> str:
    return _to_ascii(s) if ascii_mode else s

# -------- Firma ----------
def _fmt_sig(sig: Dict[str,Any], idx: int, ascii_mode: bool) -> str:
    quien = sig.get("signer_cn") or sig.get("signer_display") or sig.get("name_hint") or sig.get("issuer_cn") or ""
    fecha = sig.get("signing_time_iso") or sig.get("signing_time") or ""
    emisor = sig.get("issuer_cn") or ""
    serial = sig.get("sid_serial_hex") or ""
    subf  = sig.get("subfilter") or ""
    # Validacion sintactica minima (no valida criptografia):
    ok_sintaxis = "OK" if subf else "ND"
    lines = [
        f"- Firma #{idx}: DETECTADA: SI",
        f"  - Validez sintactica: {ok_sintaxis}",
        f"  - Fecha: {fecha}",
        f"  - Quien firma: {quien}",
        f"  - Emisor: {emisor}",
        f"  - Serial: {serial}",
        f"  - SubFilter: {subf}",
        f"  - Nota: Validacion criptografica no incluida (sin OCSP/CRL).",
    ]
    txt = "\n".join(lines)
    return _out(txt, ascii_mode)

def _best_sig_brief(sigs: List[Dict[str,Any]]) -> Tuple[str, str]:
    """
    Retorna (quien, fecha) del primer candidato mas informativo.
    """
    if not sigs:
        return ("(sin firmas)", "")
    s = sigs[0]
    quien = s.get("signer_cn") or s.get("signer_display") or s.get("name_hint") or s.get("issuer_cn") or "(desconocido)"
    fecha = s.get("signing_time_iso") or s.get("signing_time") or ""
    return (quien, fecha)

# -------- Secciones ----------
def _section(title: str, body: str, ascii_mode: bool) -> str:
    t = _out(title, ascii_mode)
    b = _out(body, ascii_mode)
    return f"{t}\n{SUB}\n{b}\n"

def _report_for_file(path: str, min_dir_score: float, ascii_mode: bool) -> str:
    try:
        full, pages, meta = extract_text_with_meta(path, min_chars_for_native=40)
    except Exception:
        full, pages, meta = "", [], {"pages_total": 0, "ocr_pages": [], "native_pages": []}

    director = find_director_mentions(full or "", min_score=min_dir_score)
    sigs_all = [s for s in extract_signatures(path) if s.get("status") != "dss-present"]
    ents = extract_entities(full or "")

    # Resumen corto por archivo
    quien_firma, fecha_firma = _best_sig_brief(sigs_all)
    count_firmas = len(sigs_all)

    cedulas = ents.get("cedulas", [])
    rucs    = ents.get("rucs", [])
    fechas  = ents.get("fechas", [])

    resumen_lines = [
        f"Archivo: {path}",
        f"Firmas encontradas: {count_firmas}",
        f"Firmante principal: {quien_firma}",
        f"Fecha de firma: {fecha_firma}",
        f"Director detectado: {'SI' if director.get('found') else 'NO'} (score {director.get('score')})",
        f"Cedulas: {len(cedulas)} | RUC: {len(rucs)} | Fechas: {len(fechas)}",
        f"OCR: {len(meta.get('ocr_pages',[]))} / {meta.get('pages_total',0)} pagina(s)",
    ]
    resumen = _out("\n".join(resumen_lines), ascii_mode)

    # Firma(s)
    if sigs_all:
        firma_body = "\n".join(_fmt_sig(s, i+1, ascii_mode) for i, s in enumerate(sigs_all))
    else:
        firma_body = _out("- No se detectaron firmas.", ascii_mode)

    # Director
    if director.get("found"):
        dir_body = f"- Detectado: SI (score {director.get('score')})\n  - Linea: {director.get('line')}\n  - Contexto: {director.get('role_context') or ''}"
    else:
        dir_body = f"- Detectado: NO (mejor score {director.get('score')})"

    # Entidades (corta)
    def _join(lst: List[str], n: int) -> str:
        if not lst:
            return "(sin datos)"
        x = lst[:n]
        return ", ".join(x)

    energia = ", ".join([f"{e['valor']} {e['unidad']}" for e in ents.get("energia", [])]) or "(sin datos)"
    fechas_s = _join(fechas, 7)
    ced_s    = _join(cedulas, 7)
    ruc_s    = _join(rucs, 7)
    nombres  = _join(ents.get("nombres_probables", []), 8)

    ocr_info = f"{len(meta.get('ocr_pages',[]))} de {meta.get('pages_total',0)} pagina(s) pasaron por OCR."

    sections = [
        SEP,
        _out(f"ARCHIVO: {path}", ascii_mode),
        SEP,
        _section("RESUMEN", resumen, ascii_mode),
        _section("FIRMA ELECTRONICA", firma_body, ascii_mode),
        _section("DIRECTOR COMERCIAL", dir_body, ascii_mode),
        _section("ENTIDADES EXTRAIDAS", f"- Cedulas validas: {ced_s}\n- RUC validos: {ruc_s}\n- Fechas: {fechas_s}\n- Datos energeticos: {energia}\n- Nombres detectados (probables): {nombres}", ascii_mode),
        _section("ESTADISTICAS OCR", f"- {ocr_info}", ascii_mode)
    ]
    return "\n".join(sections)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="PDF o carpeta")
    ap.add_argument("--out", required=True, help="Ruta del TXT de salida")
    args = ap.parse_args()

    cfg = _load_cfg()
    min_dir_score = float(cfg.get("director", {}).get("min_score", 63.0))
    ascii_mode = bool(cfg.get("report", {}).get("ascii_mode", True))
    encoding = "ascii" if ascii_mode else "utf-8-sig"

    # Reune targets
    targets: List[str] = []
    if os.path.isdir(args.input):
        for root, _, files in os.walk(args.input):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    targets.append(os.path.join(root, fn))
    else:
        targets.append(args.input)
    targets = sorted(targets)

    chunks: List[str] = []
    lote = len(targets) > 1

    # Resumen lote (si aplica)
    if lote:
        head = [
            SEP,
            "RESUMEN LOTE",
            SEP,
            f"Total de archivos: {len(targets)}",
            ""
        ]
        chunks.append("\n".join(head))

    # Procesa uno a uno
    for p in targets:
        try:
            chunks.append(_report_for_file(p, min_dir_score, ascii_mode))
        except Exception as e:
            err = f"{SEP}\nARCHIVO: {p}\n{SEP}\nERROR: {e}\n"
            chunks.append(_to_ascii(err) if ascii_mode else err)

    with open(args.out, "w", encoding=encoding, errors="ignore") as fh:
        fh.write("\n\n".join(chunks).rstrip() + "\n")

if __name__ == "__main__":
    main()
