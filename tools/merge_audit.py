Set-Content -Encoding UTF8 -Path .\tools\merge_audit.py -Value @'
from __future__ import annotations
import os, sys, json, csv

def _load(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def main(outdir):
    ocr_dir = os.path.join(outdir, "ocr")
    sig_un = os.path.join(outdir, "sig_untrusted.json")
    sig_tr = os.path.join(outdir, "sig_trusted.json")
    sig_app = os.path.join(outdir, "sig_appearance_ocr.json")

    # map: base_name -> ocr meta
    ocr_map = {}
    if os.path.isdir(ocr_dir):
        for fn in os.listdir(ocr_dir):
            if fn.lower().endswith(".json"):
                data = _load(os.path.join(ocr_dir, fn)) or {}
                base = os.path.splitext(fn)[0]
                ocr_map[base] = data

    un_data = _load(sig_un) or []
    tr_data = _load(sig_tr) or []
    ap_data = _load(sig_app) or []

    # index by file path
    def base(p): 
        return os.path.splitext(os.path.basename(p or ""))[0]

    un_idx = { base(x.get("file","")): x for x in un_data }
    tr_idx = { base(x.get("file","")): x for x in tr_data }
    ap_idx = { base(x.get("file","")): x for x in ap_data }

    rows = []
    for b in sorted(set(list(ocr_map.keys()) + list(un_idx.keys()) + list(tr_idx.keys()) + list(ap_idx.keys()))):
        ocr = ocr_map.get(b, {})
        un  = un_idx.get(b, {})
        tr  = tr_idx.get(b, {})
        ap  = ap_idx.get(b, {})

        # firmas: contar y trusted?
        un_cnt = len((un.get("signatures") or []))
        tr_cnt = len((tr.get("signatures") or []))
        # si trusted tiene al menos una con summary que contenga "VALID" (heurística) o flag 'trusted'
        any_trusted = False
        for s in tr.get("signatures") or []:
            if s.get("trusted") or ("VALID" in (s.get("summary") or "").upper()):
                any_trusted = True
                break

        rows.append({
            "file_base": b,
            "pages": ocr.get("pages"),
            "ocr_method": ocr.get("method"),
            "chars_total": ocr.get("chars_total"),
            "sig_count_untrusted": un_cnt,
            "sig_count_trusted": tr_cnt,
            "any_trusted": any_trusted,
            "sig_appearance_boxes": (ap.get("found_boxes") if isinstance(ap.get("found_boxes"), int) else None),
        })

    # CSV
    csv_path = os.path.join(outdir, "audit_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else 
                           ["file_base","pages","ocr_method","chars_total","sig_count_untrusted","sig_count_trusted","any_trusted","sig_appearance_boxes"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps({"csv": csv_path, "rows": len(rows)}, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python tools/merge_audit.py <outdir>")
        raise SystemExit(1)
    main(sys.argv[1])
'@
