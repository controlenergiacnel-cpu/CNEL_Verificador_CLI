from __future__ import annotations
import sys, json
from app.core.pdf_text import extract_text
from app.core.director import find_director_mentions

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.diag_director <archivo.pdf>")
        raise SystemExit(1)
    pdf = sys.argv[1]
    full, _ = extract_text(pdf, min_chars_for_native=40)
    res = find_director_mentions(full)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
