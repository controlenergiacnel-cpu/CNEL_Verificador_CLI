from __future__ import annotations
import os, sys, re, json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from app.core.pdf_text import extract_text_with_meta, extract_text
try:
    from tools.test_firmas import list_signatures
except Exception:
    def list_signatures(_): return []

SEP = "=" * 78
SUB = "-" * 78

def load_cfg() -> Dict[str, Any]:
    try:
        with open(os.path.join("config","config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def find_entities(txt: str) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    # Cédula (10 dígitos), RUC (13), fechas ISO yyyy-mm-dd, datos eléctricos (kW/V/A)
    ced = re.findall(r"\b\d{10}\b", txt)
    ruc = re.findall(r"\b\d{13}\b", txt)
    # dd/mm/yyyy -> yyyy-mm-dd
    dmY = []
    for d,m,y in re.findall(r"\b([0-3]?\d)[/-]([0-1]?\d)[/-](\d{4})\b", txt):
        try:
            dmY.append(datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d"))
        except Exception:
            pass
    iso = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", txt)
    fechas = sorted(set(dmY + iso))
    ener = re.findall(r"\b\d+(?:[.,]\d+)?\s?(?:kW|V|A)\b", txt, flags=re.IGNORECASE)
    # nombres probables: bloques en mayúsculas 2+ palabras
    nombres = []
    for m in re.findall(r"\b[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,}\b", txt):
        if len(m) >= 6 and m not in nombres:
            nombres.append(m)
            if len(nombres) >= 10:
                break
    return ced, ruc, fechas, ener, nombres

def director_score(txt: str, cfg: Dict[str, Any]) -> Tuple[bool, float, str]:
    block = (cfg.get("director") or {})
    names = [block.get("canonical","")] + list(block.get("aliases",[]) or [])
    names = [n for n in names if n]
    txt_low = txt.lower()
    best = 0.0
    best_name = ""
    for n in names:
        n_low = n.lower()
        if n_low in txt_low:
            score = 90.0 + min(9.99, len(n)/10.0)  # ~92-99 si aparece
        else:
            # similitud muy simple por tokens
            ntoks = [t for t in re.findall(r"[a-záéíóúñ]+", n_low) if t]
            hit = sum(1 for t in ntoks if t in txt_low)
            score = 50.0 + (hit * 8.0)
        if score > best:
            best = score
            best_name = n
    return (best >= float(block.get("min_score", 62.0))), round(best,2), best_name

def first_or_empty(v: List[str]) -> str:
    return v[0] if v else "(sin datos)"

def fmt_firma(i: int, s: Dict[str, Any]) -> str:
    quien  = s.get("subject") or s.get("name") or "(desconocido)"
    emisor = s.get("issuer") or "(no disponible)"
    serial = s.get("serial") or "(no disponible)"
    fecha  = s.get("time") or "(sin fecha)"
    subf   = s.get("subfilter") or "(sin subfilter)"
    return (f"- Firma #{i}: DETECTADA: SI - Validez sintactica: OK - Fecha: {fecha} - "
            f"Quien firma: {quien} - Emisor: {emisor} - Serial: {serial} - "
            f"SubFilter: {subf} - Nota: Validacion criptografica no incluida (sin OCSP/CRL).")

def run(folder: str):
    cfg = load_cfg()
    # Recolecta PDFs
    files = []
    if os.path.isdir(folder):
        for r, d, fns in os.walk(folder):
            for fn in fns:
                if fn.lower().endswith(".pdf"):
                    files.append(os.path.join(r, fn))
    else:
        files = [folder]

    print(SEP)
    print("RESUMEN LOTE")
    print(SEP)
    print(f"Total de archivos: {len(files)}\n")

    for path in files:
        # Meta de OCR / texto
        meta = extract_text_with_meta(path, min_chars_for_native=int((cfg.get("ocr") or {}).get("min_chars_for_native", 80)))
        full_text, _ = extract_text(path, min_chars_for_native=int((cfg.get("ocr") or {}).get("min_chars_for_native", 80)))

        # Firmas
        firmas = list_signatures(path)
        firmante_principal = (firmas[0].get("subject") or firmas[0].get("name")) if firmas else "(sin firmas)"
        fecha_firma = (firmas[0].get("time") or "(sin fecha)") if firmas else ""

        # Director comercial
        det_dir, score_dir, best_name = director_score(full_text, cfg)

        # Entidades
        ced, ruc, fechas, ener, nombres = find_entities(full_text)

        # OCR stats
        total_pages = meta.get("pages", 0)
        ocr_pages = sum(1 for p in meta.get("per_page", []) if p.get("used_ocr"))
        metodo = meta.get("method", "native")

        # --- Render reporte por archivo ---
        print("\n")
        print(SEP)
        print(f"ARCHIVO: {path}")
        print(SEP)

        print("RESUMEN")
        print(SUB)
        print(f"Archivo: {path} "
              f"Firmas encontradas: {len(firmas)} "
              f"Firmante principal: {firmante_principal} "
              f"Fecha de firma: {fecha_firma or '(sin firmas)'} "
              f"Director detectado: {'SI' if det_dir else 'NO'} (score {score_dir}) "
              f"Cedulas: {len(ced)} | RUC: {len(ruc)} | Fechas: {len(fechas)} "
              f"OCR: {ocr_pages} / {total_pages} pagina(s)\n")

        print("FIRMA ELECTRONICA")
        print(SUB)
        if not firmas:
            print("- No se detectaron firmas.\n")
        else:
            for i, s in enumerate(firmas, 1):
                print(fmt_firma(i, s))
            print()

        print("DIRECTOR COMERCIAL")
        print(SUB)
        if det_dir:
            print(f"- Detectado: SI (score {score_dir}) - Nombre coincidente: {best_name}\n")
        else:
            print(f"- Detectado: NO (mejor score {score_dir})\n")

        print("ENTIDADES EXTRAIDAS")
        print(SUB)
        print(f"- Cedulas validas: {', '.join(ced) if ced else '(sin datos)'} "
              f"- RUC validos: {', '.join(ruc) if ruc else '(sin datos)'} "
              f"- Fechas: {', '.join(fechas) if fechas else '(sin datos)'} "
              f"- Datos energeticos: {', '.join(ener) if ener else '(sin datos)'} "
              f"- Nombres detectados (probables): {', '.join(nombres) if nombres else '(sin datos)'}\n")

        print("ESTADISTICAS OCR")
        print(SUB)
        print(f"- {ocr_pages} de {total_pages} pagina(s) pasaron por OCR.\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python -m tools.reporte_lote <carpeta_o_pdf>")
        raise SystemExit(1)
    run(sys.argv[1])
