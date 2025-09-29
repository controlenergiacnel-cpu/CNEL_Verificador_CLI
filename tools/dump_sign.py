from __future__ import annotations
import json
import sys
from app.core.signatures_robust import extract_signatures

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m tools.dump_sign <archivo.pdf>")
        sys.exit(1)
    pdf = sys.argv[1]
    data = extract_signatures(pdf)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
