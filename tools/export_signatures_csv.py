from __future__ import annotations
import os, csv, argparse
from typing import List, Dict, Any
from app.core.signatures_robust import extract_signatures

def rows_for_file(path: str) -> List[Dict[str, Any]]:
    sigs = extract_signatures(path)
    rows = []
    for s in sigs:
        rows.append({
            "file": path,
            "status": s.get("status") or "",
            "subfilter": s.get("subfilter") or "",
            "signer_display": s.get("signer_display") or s.get("signer_cn") or s.get("name_hint") or "",
            "signer_cn": s.get("signer_cn") or "",
            "issuer_cn": s.get("issuer_cn") or "",
            "signing_time_iso": s.get("signing_time_iso") or s.get("signing_time") or "",
            "sid_serial_hex": s.get("sid_serial_hex") or "",
            "sid_issuer_dn": s.get("sid_issuer_dn") or "",
            "reason": s.get("reason") or "",
            "location": s.get("location") or "",
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="PDF o carpeta")
    ap.add_argument("--out", default="signatures.csv", help="Ruta CSV de salida")
    args = ap.parse_args()

    targets = []
    if os.path.isdir(args.input):
        for root, _, files in os.walk(args.input):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    targets.append(os.path.join(root, fn))
    else:
        targets.append(args.input)

    # UTF-8 con BOM para que Excel lo abra con tildes ok en Windows
    with open(args.out, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "file","status","subfilter","signer_display","signer_cn","issuer_cn",
            "signing_time_iso","sid_serial_hex","sid_issuer_dn","reason","location"
        ])
        writer.writeheader()
        for p in targets:
            for row in rows_for_file(p):
                writer.writerow(row)

if __name__ == "__main__":
    main()
