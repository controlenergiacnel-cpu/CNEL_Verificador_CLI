from __future__ import annotations
import argparse, json, os
from app.core.pdf_text import extract_text
from app.core.director import find_director_mentions
from app.core.signatures_robust import extract_signatures

def scan_file(path: str):
    try:
        full, _ = extract_text(path, min_chars_for_native=40)
    except Exception:
        full = ""
    director = find_director_mentions(full)
    sigs = extract_signatures(path)
    return {"file": path, "director": director, "signatures": sigs}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="PDF o carpeta")
    args = ap.parse_args()
    target = args.input
    items = []
    if os.path.isdir(target):
        for root, _, files in os.walk(target):
            for fn in files:
                if fn.lower().endswith(".pdf"):
                    items.append(scan_file(os.path.join(root, fn)))
    else:
        items.append(scan_file(target))
    print(json.dumps(items, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
