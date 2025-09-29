import sys, json
from ..app.core.signatures_robust import verify_pdf_signatures_deep
def main():
    if len(sys.argv) < 2:
        print('Uso: python -m tools.diag_signatures archivo.pdf')
        sys.exit(1)
    pdf_path = sys.argv[1]
    res = verify_pdf_signatures_deep(pdf_path, {'trust_dir':'config/trust','allow_fetching':True})
    print(json.dumps(res, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
