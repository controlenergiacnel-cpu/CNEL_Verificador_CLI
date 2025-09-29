# -*- coding: utf-8 -*-
r"""Uso:  python tools/build_lote_report.py untrusted.json trusted.json ocr.json > reporte.txt"""
import sys, json

def load_json(path: str):
    with open(path, "rb") as f:
        raw = f.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("utf-8-sig"))

def index_by_file(items):
    return { itm.get("file"): itm for itm in items }

def fmt_line(s):
    ok = "OK" if s.get("intact") and s.get("trusted") else ("INTEGRA" if s.get("intact") else "FALLA")
    mods = s.get("modification_level") or "?"
    summ = s.get("summary") or ""
    err  = s.get("validation_error")
    extra = f" | {summ} | mod={mods}"
    if err: extra += f" | err={err}"
    return f"  - {s.get('field_name') or 'Signature'}: {ok}{extra}"

def main():
    if len(sys.argv) < 4:
        print("Error: faltan JSONs"); sys.exit(2)
    untrusted = load_json(sys.argv[1])
    trusted   = load_json(sys.argv[2])
    ocrs      = load_json(sys.argv[3])

    ix_un  = index_by_file(untrusted)
    ix_tr  = index_by_file(trusted)
    ix_ocr = index_by_file(ocrs)
    files = sorted(set(ix_un) | set(ix_tr) | set(ix_ocr))
    lines = ["REPORTE DE LOTE – Validación de firmas y OCR", ""]

    for f in files:
        lines.append(f"📄 {f}")
        sigs_src = ix_tr.get(f, ix_un.get(f, {"signatures": []}))
        for s in sigs_src.get("signatures", []):
            lines.append(fmt_line(s))
        apps = ix_ocr.get(f, {}).get("appearances", [])
        if apps:
            lines.append("  OCR:")
            for a in apps:
                if a.get("error"):
                    lines.append(f"    - p{a.get('page')}: [ERROR] {a['error']}")
                else:
                    txt = (a.get("ocr_text") or "").replace("\n"," ").strip()
                    if len(txt) > 180: txt = txt[:177] + "..."
                    lines.append(f"    - p{a.get('page')} {a.get('field_name') or ''}: {txt}")
        lines.append("")
    sys.stdout.write("\n".join(lines))

if __name__ == "__main__":
    main()
