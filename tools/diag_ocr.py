from __future__ import annotations
import sys, json
from app.core.pdf_text import extract_text_with_meta


try:
    import sys; sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.diag_ocr <archivo.pdf>")
        raise SystemExit(1)
    pdf = sys.argv[1]
    meta = extract_text_with_meta(pdf, min_chars_for_native=40)
    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

